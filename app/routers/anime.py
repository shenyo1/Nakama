"""Anime endpoints: /anime/..."""
from __future__ import annotations

import asyncio
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..config import get_settings
from ..ratelimit import limiter
from ..schemas import ApiResponse, AnimeDetail, AnimeSummary, Episode, Genre, Paginated
from ..sources import anime_source, list_anime_sources
from ..sources.base import SourceError
from ._pagination import paginate, pagination_params

router = APIRouter(prefix="/anime", tags=["anime"])


# --------------------------------------------------------------------------- #
# Multi-source search (aggregator)
# --------------------------------------------------------------------------- #


def _normalize_title(t: str) -> str:
    """Normalize a title for dedup matching."""
    if not t:
        return ""
    t = re.sub(r"[\s\W_]+", " ", t.lower()).strip()
    t = re.sub(r"\b(episode|ep|chapter|ch)\s*\d+\b", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


@router.get(
    "/search/{query}",
    summary="Search across all anime sources (deduplicated, scored)",
)
@limiter.limit(get_settings().rate_limit)
async def search_all(
    request: Request,
    query: str,
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1),
):
    """Search every anime source concurrently, deduplicate by normalized title.

    Returns a unified list with each item annotated by ``_sources`` showing
    which sources returned this title. Useful for finding the most widely
    available show.
    """
    sources = list_anime_sources()
    if not sources:
        raise HTTPException(status_code=503, detail="No anime sources configured")

    async def _one(name: str) -> tuple:
        src = anime_source(name)
        if src is None:
            return name, {"error": "not registered"}
        try:
            results = await src.search(query)
            return name, {"ok": True, "items": results if isinstance(results, list) else []}
        except Exception as e:
            return name, {"ok": False, "error": str(e)[:200]}

    tasks = [asyncio.wait_for(_one(s), timeout=20.0) for s in sources]
    finished = await asyncio.gather(*tasks, return_exceptions=True)

    by_source: dict = {}
    sources_failed: list = []
    for result in finished:
        if isinstance(result, BaseException):
            sources_failed.append({"source": "?", "error": str(result)[:200]})
            continue
        # `result` may be (name, data) tuple or BaseException
        if not isinstance(result, tuple) or len(result) != 2:
            continue
        name, data = result  # type: ignore[misc]
        by_source[name] = data
        if not data.get("ok"):
            sources_failed.append({"source": name, "error": data.get("error", "unknown")})

    merged: dict = {}
    for name, data in by_source.items():
        for item in data.get("items", []):
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("name") or ""
            key = _normalize_title(title)
            if not key:
                continue
            if key not in merged:
                merged[key] = {
                    **item,
                    "_sources": [],
                    "_source_count": 0,
                }
            merged[key]["_sources"].append(name)
            merged[key]["_source_count"] = len(merged[key]["_sources"])

    items = sorted(
        merged.values(),
        key=lambda x: (-x.get("_source_count", 0), x.get("title", "")),
    )

    paged = paginate(items, page, page_size)
    # paginate returns List when no pagination requested, Paginated model when it is.
    # Build a uniform dict shape that includes merge-specific metadata.
    if isinstance(paged, list):
        result: dict = {
            "items": paged,
            "page": page or 1,
            "page_size": None,
            "total": len(items),
        }
    else:
        result = paged.model_dump() if hasattr(paged, "model_dump") else dict(paged)
    result["sources_failed"] = sources_failed
    result["sources_queried"] = sources
    result["merged_unique_titles"] = len(merged)
    return ApiResponse(source="multi", data=result)


def _get(source: str):
    src = anime_source(source)
    if src is None:
        raise HTTPException(status_code=404, detail=f"Unknown anime source '{source}'. Available: {list_anime_sources()}")
    return src


@router.get("/", summary="Anime documentation / source list")
@limiter.limit(get_settings().rate_limit)
async def anime_index(request: Request):  # noqa: ANN001 — slowapi injects Request
    return ApiResponse(
        data={
            "message": "Nakama Anime endpoints. Use /anime/{source}/{...}.",
            "sources": list_anime_sources(),
            "default_source": "otakudesu",
            "example": "/anime/otakudesu/home",
        }
    )


@router.get("/{source}/home", response_model=ApiResponse, summary="Latest ongoing anime")
@limiter.limit(get_settings().rate_limit)
async def home(source: str, request: Request, page: Optional[int] = Query(None, ge=1), page_size: Optional[int] = Query(None, ge=1)):
    src = _get(source)

    async def _fetch():
        try:
            data = await src.home()
            return ApiResponse(source=source, data=paginate(data, page, page_size)).model_dump()
        except SourceError as e:
            raise HTTPException(status_code=502, detail=str(e))

    from ..response_cache import cached_response
    return await cached_response(request, _fetch, ttl_seconds=300)


@router.get("/{source}/search/{query}", response_model=ApiResponse, summary="Search anime")
@limiter.limit(get_settings().rate_limit)
async def search(source: str, query: str, request: Request, page: Optional[int] = Query(None, ge=1), page_size: Optional[int] = Query(None, ge=1)):
    src = _get(source)
    try:
        data = await src.search(query)
        return ApiResponse(source=source, data=paginate(data, page, page_size))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{source}/detail/{slug}", response_model=ApiResponse[AnimeDetail], summary="Anime detail")
@limiter.limit(get_settings().rate_limit)
async def detail(source: str, slug: str, request: Request):
    src = _get(source)
    try:
        return ApiResponse(source=source, data=await src.detail(slug))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{source}/episode/{slug}", summary="Stream/download links for an episode")
@limiter.limit(get_settings().rate_limit)
async def episode(source: str, slug: str, request: Request):
    src = _get(source)
    try:
        return ApiResponse(source=source, data=await src.episode(slug))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{source}/genres", response_model=ApiResponse, summary="All genres")
@limiter.limit(get_settings().rate_limit)
async def genres(source: str, request: Request, page: Optional[int] = Query(None, ge=1), page_size: Optional[int] = Query(None, ge=1)):
    src = _get(source)
    try:
        data = await src.genres()
        return ApiResponse(source=source, data=paginate(data, page, page_size))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{source}/genre/{slug}", response_model=ApiResponse, summary="Anime in a genre")
@limiter.limit(get_settings().rate_limit)
async def genre(source: str, slug: str, request: Request, page: Optional[int] = Query(None, ge=1), page_size: Optional[int] = Query(None, ge=1)):
    src = _get(source)
    try:
        data = await src.genre(slug)
        return ApiResponse(source=source, data=paginate(data, page, page_size))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))
