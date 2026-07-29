"""Nakama Originals — featured original content + creator application.

Endpoints:
  GET  /originals            — list featured/published original series
  GET  /originals/{slug}     — series detail with chapters
  POST /originals/apply      — creator application form
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..original_models import OriginalSeries, OriginalChapter, CreatorApplication
from ..schemas import ApiResponse, Paginated

router = APIRouter(prefix="/originals", tags=["originals"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ChapterOut(BaseModel):
    id: int
    chapter_number: int
    title: Optional[str] = None
    word_count: Optional[int] = None
    created_at: datetime


class OriginalSeriesOut(BaseModel):
    id: int
    title: str
    slug: str
    content_type: str
    synopsis: Optional[str] = None
    cover_url: Optional[str] = None
    banner_url: Optional[str] = None
    author_name: str
    author_bio: Optional[str] = None
    genres: Optional[str] = None
    status: str
    featured: bool
    views: int
    created_at: datetime
    updated_at: datetime


class OriginalSeriesDetailOut(OriginalSeriesOut):
    chapters: List[ChapterOut] = []


class CreatorApplicationIn(BaseModel):
    pen_name: str = Field(..., min_length=1, max_length=128)
    bio: Optional[str] = Field(None, max_length=2000)
    portfolio_url: Optional[str] = Field(None, max_length=512)
    sample_work: Optional[str] = Field(None, max_length=5000)
    content_types: str = Field(..., description="comic, novel, or both")


class CreatorApplicationOut(BaseModel):
    id: int
    user_id: int
    pen_name: str
    bio: Optional[str] = None
    portfolio_url: Optional[str] = None
    content_types: str
    status: str
    admin_notes: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _jwt_user_id(request: Request) -> Optional[int]:
    principal = getattr(request.state, "auth_principal", None) or ""
    if principal.startswith("user:"):
        try:
            return int(principal.split(":", 1)[1])
        except ValueError:
            return None
    return None


def _require_user(request: Request) -> int:
    uid = _jwt_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="JWT required for this endpoint")
    return uid


def _series_to_out(s: OriginalSeries) -> dict:
    return OriginalSeriesOut(
        id=s.id,
        title=s.title,
        slug=s.slug,
        content_type=s.content_type,
        synopsis=s.synopsis,
        cover_url=s.cover_url,
        banner_url=s.banner_url,
        author_name=s.author_name,
        author_bio=s.author_bio,
        genres=s.genres,
        status=s.status,
        featured=s.featured,
        views=s.views,
        created_at=s.created_at,
        updated_at=s.updated_at,
    ).model_dump()


def _chapter_to_out(c: OriginalChapter) -> dict:
    return ChapterOut(
        id=c.id,
        chapter_number=c.chapter_number,
        title=c.title,
        word_count=c.word_count,
        created_at=c.created_at,
    ).model_dump()


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=ApiResponse, summary="List original series")
async def list_originals(
    featured: bool = Query(True, description="Show only featured series"),
    content_type: Optional[str] = Query(None, description="Filter: comic or novel"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    """List published original series. Defaults to featured only."""
    stmt = select(OriginalSeries).where(OriginalSeries.status == "published")
    if featured:
        stmt = stmt.where(OriginalSeries.featured == True)  # noqa: E712
    if content_type:
        stmt = stmt.where(OriginalSeries.content_type == content_type)

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(OriginalSeries.featured.desc(), OriginalSeries.updated_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()

    return ApiResponse(
        data=Paginated(
            items=[_series_to_out(r) for r in rows],
            page=page,
            page_size=page_size,
            total=total,
        ).model_dump()
    )


@router.get("/{slug}", response_model=ApiResponse, summary="Original series detail")
async def get_original(
    slug: str,
    session: AsyncSession = Depends(get_session),
):
    """Get original series detail with chapter list."""
    row = (
        await session.execute(
            select(OriginalSeries).where(OriginalSeries.slug == slug)
        )
    ).scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Original series not found")

    if row.status != "published":
        raise HTTPException(status_code=404, detail="Original series not published")

    # Increment view count (best-effort)
    try:
        row.views = (row.views or 0) + 1
        await session.commit()
    except Exception:
        pass

    # Load chapters (published only)
    chapters_stmt = (
        select(OriginalChapter)
        .where(
            OriginalChapter.series_id == row.id,
            OriginalChapter.status == "published",
        )
        .order_by(OriginalChapter.chapter_number)
    )
    chapters = (await session.execute(chapters_stmt)).scalars().all()

    detail = _series_to_out(row)
    detail["chapters"] = [_chapter_to_out(c) for c in chapters]

    return ApiResponse(data=detail)


# ---------------------------------------------------------------------------
# Creator application
# ---------------------------------------------------------------------------


@router.post(
    "/apply",
    response_model=ApiResponse,
    status_code=201,
    summary="Apply to become a Nakama Originals creator",
)
async def apply_creator(
    body: CreatorApplicationIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Submit a creator application. Requires JWT auth."""
    uid = _require_user(request)

    # Check for existing pending/approved application
    existing = (
        await session.execute(
            select(CreatorApplication).where(
                CreatorApplication.user_id == uid,
                CreatorApplication.status.in_(["pending", "approved"]),
            )
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"You already have a {existing.status} application",
        )

    app = CreatorApplication(
        user_id=uid,
        pen_name=body.pen_name,
        bio=body.bio,
        portfolio_url=body.portfolio_url,
        sample_work=body.sample_work,
        content_types=body.content_types,
        status="pending",
    )
    session.add(app)
    await session.commit()
    await session.refresh(app)

    return ApiResponse(
        data=CreatorApplicationOut(
            id=app.id,
            user_id=app.user_id,
            pen_name=app.pen_name,
            bio=app.bio,
            portfolio_url=app.portfolio_url,
            content_types=app.content_types,
            status=app.status,
            admin_notes=app.admin_notes,
            created_at=app.created_at,
        ).model_dump()
    )
