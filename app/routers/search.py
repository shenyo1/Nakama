"""Cross-source search endpoint: /search?q=<query>&type=<anime|comic|novel>.

Aggregates ``search()`` across every source of the requested type and returns
results grouped by source. Each source is queried independently — a failure
in one source does not poison the others; instead the response includes a
``sources_failed`` entry alongside ``sources_tried`` so callers can tell
which adapters responded.

This complements the per-source ``/{type}/{source}/search/{query}`` routes
without duplicating any logic: it walks the source registry and awaits each
adapter's ``search()`` coroutine concurrently with ``asyncio.gather``.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, Query, Request

from ..ratelimit import limiter
from ..config import get_settings
from ..schemas import ApiResponse
from ..sources import (
    anime_source,
    comic_source,
    list_anime_sources,
    list_comic_sources,
    list_novel_sources,
    novel_source,
)
from ..sources.base import SourceError

router = APIRouter(tags=["search"])


async def _gather_search(source_names: List[str], kind: str, query: str) -> Dict[str, Any]:
    """Run every adapter's ``search(query)`` and split the outcomes.

    Returns ``{data, sources_tried, sources_failed}``. ``data`` is keyed by
    source name; ``sources_failed`` lists sources whose adapter raised —
    useful for callers who want to display partial results gracefully.
    """
    data: Dict[str, Any] = {}
    failed: List[Dict[str, str]] = []

    async def _one(name: str) -> tuple[str, Any]:
        if kind == "anime":
            src = anime_source(name)
        elif kind == "comic":
            src = comic_source(name)
        else:
            src = novel_source(name)
        if src is None:
            return name, {"error": f"source '{name}' is not a {kind} source"}
        try:
            return name, await src.search(query)
        except SourceError as e:
            return name, {"error": str(e)}
        except Exception as e:  # noqa: BLE001 — guard against adapter bugs
            return name, {"error": f"{type(e).__name__}: {e}"}

    results = await asyncio.gather(*[_one(n) for n in source_names], return_exceptions=False)
    for name, payload in results:
        # Adapter returned an error dict {"error": "..."} → record failure and skip.
        if isinstance(payload, dict) and "error" in payload and len(payload) == 1:
            failed.append({"source": name, "error": str(payload["error"])})
            continue
        data[name] = payload
    return {"data": data, "sources_failed": failed}


@router.get("/search", summary="Cross-source search (anime/comic/novel)")
@limiter.limit(get_settings().rate_limit)
async def cross_search(
    request: Request,
    q: str = Query(..., min_length=1, description="Free-text query."),
    type: str = Query("comic", description="One of: anime, comic, novel."),
):
    """Search every source of *type* for *q* and return per-source results."""
    kind = (type or "comic").lower()
    if kind not in ("anime", "comic", "novel"):
        return ApiResponse(
            ok=False,
            data={
                "error": f"Unknown type '{type}'. Must be one of: anime, comic, novel.",
                "query": q,
                "type": kind,
                "sources_tried": [],
                "results": {},
            },
        )

    if kind == "anime":
        source_names = list_anime_sources()
    elif kind == "comic":
        source_names = list_comic_sources()
    else:
        source_names = list_novel_sources()

    gathered = await _gather_search(source_names, kind, q)
    return ApiResponse(
        data={
            "query": q,
            "type": kind,
            "sources_tried": source_names,
            "sources_failed": gathered["sources_failed"],
            "results": gathered["data"],
        }
    )
