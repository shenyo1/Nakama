"""Anime endpoints: /anime/..."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..config import get_settings
from ..ratelimit import limiter
from ..schemas import ApiResponse, AnimeDetail, AnimeSummary, Episode, Genre, Paginated
from ..sources import anime_source, list_anime_sources
from ..sources.base import SourceError
from ._pagination import paginate, pagination_params

router = APIRouter(prefix="/anime", tags=["anime"])


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
    try:
        data = await src.home()
        return ApiResponse(source=source, data=paginate(data, page, page_size))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


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
