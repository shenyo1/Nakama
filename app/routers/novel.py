"""Novel endpoints: /novel/...

Mirrors the anime router shape (home/search/detail/chapter/genres/genre) plus a
``popular`` endpoint. Novel sources return *text* chapter content rather than
images, so the chapter endpoint returns a ``ChapterText`` body (paragraphs).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ..config import get_settings
from ..ratelimit import limiter
from ..schemas import ApiResponse, NovelDetail, Paginated
from ..sources import list_novel_sources, novel_source
from ..sources.base import SourceError
from ._pagination import paginate

router = APIRouter(prefix="/novel", tags=["novel"])


def _get(source: str):
    src = novel_source(source)
    if src is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown novel source '{source}'. Available: {list_novel_sources()}",
        )
    return src


@router.get("/", summary="Novel documentation / source list")
@limiter.limit(get_settings().rate_limit)
async def novel_index(request: Request):  # noqa: ANN001 — slowapi injects Request
    return ApiResponse(
        data={
            "message": "Nakama Novel endpoints. Use /novel/{source}/{...}.",
            "sources": list_novel_sources(),
            "default_source": "sakuranovel",
            "example": "/novel/sakuranovel/home",
        }
    )


@router.get(
    "/{source}/home",
    response_model=ApiResponse,
    summary="Latest novels (paginated upstream)",
)
@limiter.limit(get_settings().rate_limit)
async def home(
    source: str,
    request: Request,
    page: Optional[int] = Query(None, ge=1, description="Upstream page number"),
    page_size: Optional[int] = Query(None, ge=1),
):
    """Latest novels.

    ``page`` here is the *upstream* page (passed to the source's ``home``);
    ``page_size`` paginates the returned slice locally.
    """
    src = _get(source)
    try:
        data = await src.home(page or 1)
        return ApiResponse(source=source, data=paginate(data, None, page_size))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/{source}/search/{query}",
    response_model=ApiResponse,
    summary="Search novels",
)
@limiter.limit(get_settings().rate_limit)
async def search(
    source: str,
    query: str,
    request: Request,
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1),
):
    src = _get(source)
    try:
        data = await src.search(query)
        return ApiResponse(source=source, data=paginate(data, page, page_size))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/{source}/detail/{slug}",
    response_model=ApiResponse[NovelDetail],
    summary="Novel detail + chapter list",
)
@limiter.limit(get_settings().rate_limit)
async def detail(source: str, slug: str, request: Request):
    src = _get(source)
    try:
        return ApiResponse(source=source, data=await src.detail(slug))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/{source}/chapter/{slug}",
    response_model=ApiResponse,
    summary="Chapter text (novel prose)",
)
@limiter.limit(get_settings().rate_limit)
async def chapter(source: str, slug: str, request: Request):
    src = _get(source)
    try:
        return ApiResponse(source=source, data=await src.chapter(slug))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/{source}/genres",
    response_model=ApiResponse,
    summary="All genres",
)
@limiter.limit(get_settings().rate_limit)
async def genres(
    source: str,
    request: Request,
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1),
):
    src = _get(source)
    try:
        data = await src.genres()
        return ApiResponse(source=source, data=paginate(data, page, page_size))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/{source}/genre/{slug}",
    response_model=ApiResponse,
    summary="Novels in a genre (paginated upstream)",
)
@limiter.limit(get_settings().rate_limit)
async def genre(
    source: str,
    slug: str,
    request: Request,
    page: Optional[int] = Query(None, ge=1, description="Upstream page number"),
    page_size: Optional[int] = Query(None, ge=1),
):
    """Novels in a genre.

    ``page`` is the *upstream* genre page (passed to ``genre``); ``page_size``
    paginates the returned slice locally.
    """
    src = _get(source)
    try:
        data = await src.genre(slug, page or 1)
        return ApiResponse(source=source, data=paginate(data, None, page_size))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get(
    "/{source}/popular",
    response_model=ApiResponse,
    summary="Popular novels",
)
@limiter.limit(get_settings().rate_limit)
async def popular(
    source: str,
    request: Request,
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1),
):
    src = _get(source)
    try:
        data = await src.popular()
        return ApiResponse(source=source, data=paginate(data, page, page_size))
    except SourceError as e:
        raise HTTPException(status_code=502, detail=str(e))
