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
from ..sources.merge_search import multi_source_search, normalize_title
from ._pagination import paginate, pagination_params

router = APIRouter(prefix="/anime", tags=["anime"])


# Keep normalize_title exported for compat with tests
_ = normalize_title


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
    result = await multi_source_search(
        kind="anime",
        query=query,
        get_factory=anime_source,
        list_fn=list_anime_sources,
        page=page,
        page_size=page_size,
    )
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
            return ApiResponse(source=source, data=paginate(data, page, page_size, kind="anime", source=source)).model_dump()
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
        return ApiResponse(source=source, data=paginate(data, page, page_size, kind="anime", source=source))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{source}/detail/{slug}", response_model=ApiResponse[AnimeDetail], summary="Anime detail")
@limiter.limit(get_settings().rate_limit)
async def detail(source: str, slug: str, request: Request):
    src = _get(source)
    try:
        data = await src.detail(slug)
        from ..enrich import enrich_detail
        data = enrich_detail(data, "anime", source)
        return ApiResponse(source=source, data=data)
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
        return ApiResponse(source=source, data=paginate(data, page, page_size, kind="anime", source=source))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{source}/genre/{slug}", response_model=ApiResponse, summary="Anime in a genre")
@limiter.limit(get_settings().rate_limit)
async def genre(source: str, slug: str, request: Request, page: Optional[int] = Query(None, ge=1), page_size: Optional[int] = Query(None, ge=1)):
    src = _get(source)
    try:
        data = await src.genre(slug)
        return ApiResponse(source=source, data=paginate(data, page, page_size, kind="anime", source=source))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))
