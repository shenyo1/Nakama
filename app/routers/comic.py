"""Comic endpoints: /comic/..."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ..config import get_settings
from ..ratelimit import limiter
from ..schemas import ApiResponse, ComicDetail, ComicSummary, Paginated
from ..sources import comic_source, list_comic_sources
from ..sources.base import SourceError
from ._pagination import paginate

router = APIRouter(prefix="/comic", tags=["comic"])


def _get(source: str):
    src = comic_source(source)
    if src is None:
        raise HTTPException(status_code=404, detail=f"Unknown comic source '{source}'. Available: {list_comic_sources()}")
    return src


@router.get("/", summary="Comic documentation / source list")
@limiter.limit(get_settings().rate_limit)
async def comic_index(request: Request):  # noqa: ANN001
    return ApiResponse(
        data={
            "message": "Nakama Comic endpoints. Use /comic/{source}/{...}.",
            "sources": list_comic_sources(),
            "default_source": "komiku",
            "example": "/comic/komiku/home",
        }
    )


@router.get("/{source}/home", response_model=ApiResponse, summary="Latest comics")
@limiter.limit(get_settings().rate_limit)
async def home(source: str, request: Request, page: Optional[int] = Query(None, ge=1), page_size: Optional[int] = Query(None, ge=1)):
    src = _get(source)
    try:
        data = await src.home()
        return ApiResponse(source=source, data=paginate(data, page, page_size))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{source}/search/{query}", response_model=ApiResponse, summary="Search comics")
@limiter.limit(get_settings().rate_limit)
async def search(source: str, query: str, request: Request, page: Optional[int] = Query(None, ge=1), page_size: Optional[int] = Query(None, ge=1)):
    src = _get(source)
    try:
        data = await src.search(query)
        return ApiResponse(source=source, data=paginate(data, page, page_size))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{source}/manga/{slug}", response_model=ApiResponse[ComicDetail], summary="Comic detail + chapter list")
@limiter.limit(get_settings().rate_limit)
async def manga(source: str, slug: str, request: Request):
    src = _get(source)
    try:
        return ApiResponse(source=source, data=await src.manga(slug))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{source}/chapter/{slug:path}", summary="Chapter image list")
@limiter.limit(get_settings().rate_limit)
async def chapter(source: str, slug: str, request: Request):
    src = _get(source)
    try:
        return ApiResponse(source=source, data=await src.chapter(slug))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{source}/popular", response_model=ApiResponse, summary="Popular comics")
@limiter.limit(get_settings().rate_limit)
async def popular(source: str, request: Request, page: Optional[int] = Query(None, ge=1), page_size: Optional[int] = Query(None, ge=1)):
    src = _get(source)
    try:
        data = await src.popular()
        return ApiResponse(source=source, data=paginate(data, page, page_size))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{source}/genre/{slug}", response_model=ApiResponse, summary="Comics in a genre")
@limiter.limit(get_settings().rate_limit)
async def genre(source: str, slug: str, request: Request, page: Optional[int] = Query(None, ge=1), page_size: Optional[int] = Query(None, ge=1)):
    src = _get(source)
    try:
        data = await src.genre(slug)
        return ApiResponse(source=source, data=paginate(data, page, page_size))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{source}/latest", response_model=ApiResponse, summary="Recently updated comics")
@limiter.limit(get_settings().rate_limit)
async def latest(source: str, request: Request, page: Optional[int] = Query(None, ge=1), page_size: Optional[int] = Query(None, ge=1)):
    src = _get(source)
    try:
        data = await src.latest()
        return ApiResponse(source=source, data=paginate(data, page, page_size))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))
