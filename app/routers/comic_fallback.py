"""Comic fallback router: search/manga/chapter with auto-cross-source fallback.

Endpoints (all under /comic):

  GET /comic/search/{query}              — search across all comic sources
  GET /comic/manga/{slug}                — detail+chapters across comic sources
  GET /comic/chapter/{slug}              — first source with images wins

Each endpoint fans out concurrently across the comic source registry and:
- searches/details: aggregate results, surface per-source status
- chapter images: first non-empty image list wins; returns {source, data, sources_failed}

All three honor ``?primary=<source>`` to bias one source first (e.g. when the
caller already knows the upstream series is on a particular scraper).
"""
from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ..config import get_settings
from ..ratelimit import limiter
from ..schemas import ApiResponse
from ..sources import (
    comic_source,
    list_comic_sources,
    with_fallback,
)
from ..sources.base import SourceError

router = APIRouter(prefix="/comic", tags=["comic-fallback"])


@router.get("/search/{query}", summary="Search across comic sources with fallback")
@limiter.limit(get_settings().rate_limit)
async def fallback_search(
    request: Request,
    query: str,
    primary: Optional[str] = Query(
        None,
        description="Bias this source first (e.g. 'kiryuu'). Must be a known comic source.",
    ),
):
    primary = primary or "komiku"
    if primary not in list_comic_sources():
        raise HTTPException(
            status_code=404,
            detail=f"Unknown primary '{primary}'. Available: {list_comic_sources()}",
        )

    names = [primary] + [n for n in list_comic_sources() if n != primary]

    async def _one(name: str) -> tuple[str, Any]:
        src = comic_source(name)
        if src is None:
            return name, {"error": f"unknown comic source '{name}'"}
        try:
            return name, await src.search(query)
        except SourceError as e:
            return name, {"error": str(e)}
        except Exception as e:  # noqa: BLE001
            return name, {"error": f"{type(e).__name__}: {e}"}

    results = await asyncio.gather(*[_one(n) for n in names], return_exceptions=False)
    by_source: Dict[str, Any] = {}
    failed: List[Dict[str, str]] = []
    counts: Dict[str, int] = {}
    for name, payload in results:
        if isinstance(payload, dict) and "error" in payload and len(payload) == 1:
            failed.append({"source": name, "error": str(payload["error"])})
            continue
        by_source[name] = payload
        counts[name] = len(payload) if isinstance(payload, list) else 0
    total = sum(counts.values())

    # Build deduplicated union of results, scored by source coverage.
    # Imported lazily to avoid routers↔sources circular import at module load.
    from ..sources.merge_search import normalize_title
    merged: Dict[str, dict] = {}
    for name, items in by_source.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("name") or ""
            key = normalize_title(title)
            if not key:
                continue
            if key not in merged:
                merged[key] = {**item, "_sources": [], "_source_count": 0}
            merged[key]["_sources"].append(name)
            merged[key]["_source_count"] = len(merged[key]["_sources"])
    merged_list = sorted(
        merged.values(),
        key=lambda x: (-x.get("_source_count", 0), x.get("title", "")),
    )

    return ApiResponse(
        data={
            "query": query,
            "primary": primary,
            "sources_tried": names,
            "sources_failed": failed,
            "counts": counts,
            "total": total,
            "results": by_source,
            "merged": merged_list,
            "merged_unique_titles": len(merged),
        }
    )


@router.get(
    "/manga/{slug:path}",
    summary="Find manga detail across comic sources with fallback",
)
@limiter.limit(get_settings().rate_limit)
async def fallback_manga(
    request: Request,
    slug: str,
    primary: Optional[str] = Query(None),
):
    primary = primary or "komiku"
    if primary not in list_comic_sources():
        raise HTTPException(
            status_code=404,
            detail=f"Unknown primary '{primary}'. Available: {list_comic_sources()}",
        )

    names = [primary] + [n for n in list_comic_sources() if n != primary]

    async def _one(name: str) -> tuple[str, Any]:
        src = comic_source(name)
        if src is None:
            return name, {"error": f"unknown comic source '{name}'"}
        try:
            return name, await src.manga(slug)
        except SourceError as e:
            return name, {"error": str(e)}
        except Exception as e:  # noqa: BLE001
            return name, {"error": f"{type(e).__name__}: {e}"}

    results = await asyncio.gather(*[_one(n) for n in names], return_exceptions=False)
    success: List[tuple[str, Any]] = []
    failed: List[Dict[str, str]] = []
    for name, payload in results:
        if isinstance(payload, dict) and "error" in payload and len(payload) == 1:
            failed.append({"source": name, "error": str(payload["error"])})
        else:
            success.append((name, payload))
    if success:
        winner_name, winner_data = success[0]
        return ApiResponse(
            source=winner_name,
            data={
                "primary": primary,
                "winner": winner_name,
                "detail": winner_data,
                "sources_failed": failed,
                "matched": len(success),
            },
        )
    raise HTTPException(
        status_code=502,
        detail=f"manga '{slug}' not found in any comic source. Last errors: "
        + "; ".join(f"{f['source']}: {f['error'][:80]}" for f in failed[-3:]),
    )


_SLUG_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


@router.get(
    "/chapter/{slug:path}",
    summary="Chapter images across comic sources with fallback",
)
@limiter.limit(get_settings().rate_limit)
async def fallback_chapter(
    request: Request,
    slug: str,
    primary: Optional[str] = Query(None),
):
    """First source returning a non-empty ``images`` list wins.

    Komikcast (which needs a JWT) is intentionally last so other free sources
    can serve images first.
    """
    sources = list_comic_sources()
    primary = primary or "komiku"
    if primary not in sources:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown primary '{primary}'. Available: {sources}",
        )
    # Order: primary, then others, but komikcast last (auth-gated).
    others = [n for n in sources if n != primary and n != "komikcast"]
    if primary != "komikcast":
        names = [primary] + others + ["komikcast"]
    else:
        names = ["komikcast"] + others

    async def _one(name: str) -> tuple[str, Any]:
        src = comic_source(name)
        if src is None:
            return name, {"error": "unknown"}
        try:
            return name, await src.chapter(slug)
        except SourceError as e:
            return name, {"error": str(e)}
        except Exception as e:  # noqa: BLE001
            return name, {"error": f"{type(e).__name__}: {e}"}

    results = await asyncio.gather(*[_one(n) for n in names], return_exceptions=False)
    failed: List[Dict[str, str]] = []
    for name, payload in results:
        if isinstance(payload, dict) and "error" in payload and len(payload) == 1:
            failed.append({"source": name, "error": str(payload["error"])})
            continue
        imgs = payload.get("images") if isinstance(payload, dict) else None
        if imgs:
            return ApiResponse(
                source=name,
                data={
                    "winner": name,
                    "image_count": len(imgs),
                    "primary": primary,
                    "chapter": payload,
                    "sources_failed": failed,
                },
            )
    # No images anywhere — return best metadata we have (first non-error).
    last_meta: Optional[tuple[str, Any]] = None
    for name, payload in results:
        if not (isinstance(payload, dict) and "error" in payload and len(payload) == 1):
            last_meta = (name, payload)
            break
    if last_meta:
        name, payload = last_meta
        return ApiResponse(
            source=name,
            data={
                "winner": None,
                "image_count": 0,
                "primary": primary,
                "chapter": payload,
                "sources_failed": failed,
                "notes": "No source returned images; got metadata only. "
                "Use /sources/health to inspect.",
            },
        )
    raise HTTPException(
        status_code=502,
        detail="chapter not found in any comic source. Last errors: "
        + "; ".join(f"{f['source']}: {f['error'][:80]}" for f in failed[-3:]),
    )