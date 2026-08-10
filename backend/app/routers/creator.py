"""Creator endpoints: register, series CRUD, chapters, dashboard.

POST   /creator/register      — register as a creator
GET    /creator/profile       — get own creator profile
PUT    /creator/profile       — update own creator profile
POST   /creator/series        — create a new series
GET    /creator/series        — list own series
GET    /creator/series/{id}   — get series detail with chapters
PUT    /creator/series/{id}   — update series metadata
DELETE /creator/series/{id}   — delete series (cascades chapters)
POST   /creator/chapters      — upload a chapter
PUT    /creator/chapters/{id} — update chapter content
DELETE /creator/chapters/{id} — delete chapter
GET    /creator/dashboard     — stats: views, followers, revenue estimate
POST   /creator/follow/{creator_id}      — follow a creator
DELETE /creator/follow/{creator_id}      — unfollow
GET    /creator/followers                — list who I follow
GET    /creator/browse                   — browse all creators (public)
GET    /creator/browse/{creator_id}      — view a creator's public profile + series
GET    /creator/browse/{creator_id}/series/{series_id}  — view a public series + chapters
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..creator_models import (
    CreatorProfile,
    CreatorSeries,
    CreatorChapter,
    CreatorFollower,
)
from ..dependencies import current_user_required

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/creator", tags=["creator"])

# ---------------------------------------------------------------------------
# Upload directory for cover images
# ---------------------------------------------------------------------------
_UPLOAD_DIR = Path(os.getenv("CREATOR_UPLOAD_DIR", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "creator"
)))
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_UPLOAD_MB = int(os.getenv("CREATOR_MAX_UPLOAD_MB", "5"))


def _safe_filename(original: str) -> str:
    """Generate a unique, safe filename for uploaded images."""
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {ext}")
    return f"{uuid.uuid4().hex}{ext}"


async def _save_upload(file: UploadFile) -> str:
    """Save an uploaded image and return the relative URL path."""
    if file.size and file.size > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File exceeds {MAX_UPLOAD_MB}MB limit")
    filename = _safe_filename(file.filename or "image.png")
    dest = _UPLOAD_DIR / filename
    with open(dest, "wb") as f:
        content = await file.read()
        f.write(content)
    return f"/uploads/creator/{filename}"


async def _get_or_create_creator_profile(
    user, session: AsyncSession
) -> CreatorProfile:
    """Get existing profile or raise 404 if not registered."""
    result = await session.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Creator profile not found. Register first via POST /creator/register")
    return profile


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class RegisterBody(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=128)
    bio: Optional[str] = Field(None, max_length=2000)
    social_links: dict = Field(default_factory=dict)


class ProfileOut(BaseModel):
    id: int
    user_id: int
    display_name: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    social_links: dict = {}
    follower_count: int = 0
    total_views: int = 0
    verified: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=128)
    bio: Optional[str] = Field(None, max_length=2000)
    social_links: Optional[dict] = None


class SeriesCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    kind: str = Field(..., pattern=r"^(novel|comic|art)$")
    cover_image: Optional[str] = None


class SeriesUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    kind: Optional[str] = Field(None, pattern=r"^(novel|comic|art)$")
    cover_image: Optional[str] = None
    status: Optional[str] = Field(None, pattern=r"^(ongoing|completed|hiatus)$")
    published: Optional[bool] = None


class SeriesOut(BaseModel):
    id: int
    creator_id: int
    title: str
    description: Optional[str] = None
    kind: str
    cover_image: Optional[str] = None
    status: str = "ongoing"
    chapter_count: int = 0
    total_views: int = 0
    published: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChapterCreate(BaseModel):
    series_id: int
    title: str = Field(..., min_length=1, max_length=255)
    chapter_number: int = Field(..., ge=1)
    content: str = Field(..., min_length=1)
    content_format: str = Field(default="markdown", pattern=r"^(markdown|html)$")
    published: bool = False


class ChapterUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    chapter_number: Optional[int] = Field(None, ge=1)
    content: Optional[str] = Field(None, min_length=1)
    content_format: Optional[str] = Field(None, pattern=r"^(markdown|html)$")
    published: Optional[bool] = None


class ChapterOut(BaseModel):
    id: int
    series_id: int
    title: str
    chapter_number: int
    content: str = ""
    content_format: str = "markdown"
    word_count: int = 0
    views: int = 0
    published: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DashboardOut(BaseModel):
    profile: ProfileOut
    series_count: int
    total_chapters: int
    total_views: int
    total_followers: int
    revenue_estimate: float  # mock estimate in USD
    recent_series: list[SeriesOut]
    top_chapters: list[ChapterOut]


class CreatorBrowseItem(BaseModel):
    id: int
    display_name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    follower_count: int = 0
    series_count: int = 0
    verified: bool = False

    model_config = {"from_attributes": True}


class FollowStatus(BaseModel):
    following: bool
    follower_count: int


# ---------------------------------------------------------------------------
# Endpoints: Registration & Profile
# ---------------------------------------------------------------------------

@router.post("/register", response_model=ProfileOut)
async def register_creator(
    body: RegisterBody,
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Register the authenticated user as a creator."""
    # Check if already registered
    existing = await session.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already registered as a creator")

    profile = CreatorProfile(
        user_id=user.id,
        display_name=body.display_name,
        bio=body.bio,
        social_links=body.social_links,
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile


@router.get("/profile", response_model=ProfileOut)
async def get_my_profile(
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Get the authenticated user's creator profile."""
    profile = await _get_or_create_creator_profile(user, session)
    return profile


@router.put("/profile", response_model=ProfileOut)
async def update_my_profile(
    body: ProfileUpdate,
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Update the authenticated user's creator profile."""
    profile = await _get_or_create_creator_profile(user, session)
    if body.display_name is not None:
        profile.display_name = body.display_name
    if body.bio is not None:
        profile.bio = body.bio
    if body.social_links is not None:
        profile.social_links = body.social_links
    await session.commit()
    await session.refresh(profile)
    return profile


@router.post("/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Upload a creator avatar image."""
    profile = await _get_or_create_creator_profile(user, session)
    url = await _save_upload(file)
    profile.avatar_url = url
    await session.commit()
    await session.refresh(profile)
    return {"ok": True, "avatar_url": url}


# ---------------------------------------------------------------------------
# Endpoints: Series CRUD
# ---------------------------------------------------------------------------

@router.post("/series", response_model=SeriesOut)
async def create_series(
    body: SeriesCreate,
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Create a new series under the authenticated creator."""
    profile = await _get_or_create_creator_profile(user, session)
    series = CreatorSeries(
        creator_id=profile.id,
        title=body.title,
        description=body.description,
        kind=body.kind,
        cover_image=body.cover_image,
    )
    session.add(series)
    await session.commit()
    await session.refresh(series)
    return series


@router.get("/series", response_model=list[SeriesOut])
async def list_my_series(
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
    kind: Optional[str] = Query(None, pattern=r"^(novel|comic|art)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List the authenticated creator's series."""
    profile = await _get_or_create_creator_profile(user, session)
    q = select(CreatorSeries).where(CreatorSeries.creator_id == profile.id)
    if kind:
        q = q.where(CreatorSeries.kind == kind)
    q = q.order_by(desc(CreatorSeries.updated_at)).offset(offset).limit(limit)
    result = await session.execute(q)
    return result.scalars().all()


@router.get("/series/{series_id}", response_model=SeriesOut)
async def get_my_series(
    series_id: int,
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Get a single series with its chapters."""
    profile = await _get_or_create_creator_profile(user, session)
    result = await session.execute(
        select(CreatorSeries).where(
            and_(CreatorSeries.id == series_id, CreatorSeries.creator_id == profile.id)
        )
    )
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    return series


@router.put("/series/{series_id}", response_model=SeriesOut)
async def update_series(
    series_id: int,
    body: SeriesUpdate,
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Update series metadata."""
    profile = await _get_or_create_creator_profile(user, session)
    result = await session.execute(
        select(CreatorSeries).where(
            and_(CreatorSeries.id == series_id, CreatorSeries.creator_id == profile.id)
        )
    )
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    if body.title is not None:
        series.title = body.title
    if body.description is not None:
        series.description = body.description
    if body.kind is not None:
        series.kind = body.kind
    if body.cover_image is not None:
        series.cover_image = body.cover_image
    if body.status is not None:
        series.status = body.status
    if body.published is not None:
        series.published = body.published

    await session.commit()
    await session.refresh(series)
    return series


@router.delete("/series/{series_id}")
async def delete_series(
    series_id: int,
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Delete a series and all its chapters."""
    profile = await _get_or_create_creator_profile(user, session)
    result = await session.execute(
        select(CreatorSeries).where(
            and_(CreatorSeries.id == series_id, CreatorSeries.creator_id == profile.id)
        )
    )
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    await session.delete(series)
    await session.commit()
    return {"ok": True, "deleted": series_id}


# ---------------------------------------------------------------------------
# Endpoints: Chapters CRUD
# ---------------------------------------------------------------------------

@router.post("/chapters", response_model=ChapterOut)
async def create_chapter(
    body: ChapterCreate,
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Upload a new chapter to a series owned by the authenticated creator."""
    profile = await _get_or_create_creator_profile(user, session)
    # Verify series ownership
    result = await session.execute(
        select(CreatorSeries).where(
            and_(CreatorSeries.id == body.series_id, CreatorSeries.creator_id == profile.id)
        )
    )
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found or not yours")

    # Check for duplicate chapter number
    dup = await session.execute(
        select(CreatorChapter).where(
            and_(
                CreatorChapter.series_id == body.series_id,
                CreatorChapter.chapter_number == body.chapter_number,
            )
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Chapter {body.chapter_number} already exists in this series",
        )

    word_count = len(body.content.split()) if body.content else 0
    chapter = CreatorChapter(
        series_id=body.series_id,
        title=body.title,
        chapter_number=body.chapter_number,
        content=body.content,
        content_format=body.content_format,
        word_count=word_count,
        published=body.published,
    )
    session.add(chapter)
    # Update chapter_count on series
    series.chapter_count = (series.chapter_count or 0) + 1
    await session.commit()
    await session.refresh(chapter)
    return chapter


@router.get("/chapters/{chapter_id}", response_model=ChapterOut)
async def get_my_chapter(
    chapter_id: int,
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Get a single chapter (must own the parent series)."""
    profile = await _get_or_create_creator_profile(user, session)
    result = await session.execute(
        select(CreatorChapter)
        .join(CreatorSeries)
        .where(
            and_(
                CreatorChapter.id == chapter_id,
                CreatorSeries.creator_id == profile.id,
            )
        )
    )
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


@router.put("/chapters/{chapter_id}", response_model=ChapterOut)
async def update_chapter(
    chapter_id: int,
    body: ChapterUpdate,
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Update chapter content or metadata."""
    profile = await _get_or_create_creator_profile(user, session)
    result = await session.execute(
        select(CreatorChapter)
        .join(CreatorSeries)
        .where(
            and_(
                CreatorChapter.id == chapter_id,
                CreatorSeries.creator_id == profile.id,
            )
        )
    )
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    if body.title is not None:
        chapter.title = body.title
    if body.chapter_number is not None:
        chapter.chapter_number = body.chapter_number
    if body.content is not None:
        chapter.content = body.content
        chapter.word_count = len(body.content.split())
    if body.content_format is not None:
        chapter.content_format = body.content_format
    if body.published is not None:
        chapter.published = body.published

    await session.commit()
    await session.refresh(chapter)
    return chapter


@router.delete("/chapters/{chapter_id}")
async def delete_chapter(
    chapter_id: int,
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Delete a chapter."""
    profile = await _get_or_create_creator_profile(user, session)
    result = await session.execute(
        select(CreatorChapter)
        .join(CreatorSeries)
        .where(
            and_(
                CreatorChapter.id == chapter_id,
                CreatorSeries.creator_id == profile.id,
            )
        )
    )
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    series_id = chapter.series_id
    await session.delete(chapter)
    # Decrement chapter_count
    sresult = await session.execute(select(CreatorSeries).where(CreatorSeries.id == series_id))
    series = sresult.scalar_one_or_none()
    if series:
        series.chapter_count = max(0, (series.chapter_count or 1) - 1)
    await session.commit()
    return {"ok": True, "deleted": chapter_id}


# ---------------------------------------------------------------------------
# Endpoint: Upload cover image
# ---------------------------------------------------------------------------

@router.post("/upload/cover")
async def upload_cover(
    file: UploadFile = File(...),
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Upload a cover image for a series. Returns the URL to use in series create/update."""
    await _get_or_create_creator_profile(user, session)  # Verify creator exists
    url = await _save_upload(file)
    return {"ok": True, "url": url}


# ---------------------------------------------------------------------------
# Endpoint: Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=DashboardOut)
async def creator_dashboard(
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Get creator dashboard with stats."""
    profile = await _get_or_create_creator_profile(user, session)

    # Series count
    scount_result = await session.execute(
        select(func.count(CreatorSeries.id)).where(
            CreatorSeries.creator_id == profile.id
        )
    )
    series_count = scount_result.scalar() or 0

    # Total chapters
    chcount_result = await session.execute(
        select(func.count(CreatorChapter.id))
        .join(CreatorSeries)
        .where(CreatorSeries.creator_id == profile.id)
    )
    total_chapters = chcount_result.scalar() or 0

    # Total views across all series
    tviews_result = await session.execute(
        select(func.coalesce(func.sum(CreatorSeries.total_views), 0)).where(
            CreatorSeries.creator_id == profile.id
        )
    )
    total_views = tviews_result.scalar() or 0

    # Recent series (last 5)
    recent_result = await session.execute(
        select(CreatorSeries)
        .where(CreatorSeries.creator_id == profile.id)
        .order_by(desc(CreatorSeries.updated_at))
        .limit(5)
    )
    recent_series = recent_result.scalars().all()

    # Top chapters by views (last 5)
    top_result = await session.execute(
        select(CreatorChapter)
        .join(CreatorSeries)
        .where(CreatorSeries.creator_id == profile.id)
        .order_by(desc(CreatorChapter.views))
        .limit(5)
    )
    top_chapters = top_result.scalars().all()

    # Revenue estimate: crude mock based on views
    # $0.002 per view (CPM $2) — purely illustrative
    revenue_estimate = round(total_views * 0.002, 2)

    return DashboardOut(
        profile=ProfileOut.model_validate(profile),
        series_count=series_count,
        total_chapters=total_chapters,
        total_views=total_views,
        total_followers=profile.follower_count or 0,
        revenue_estimate=revenue_estimate,
        recent_series=[SeriesOut.model_validate(s) for s in recent_series],
        top_chapters=[ChapterOut.model_validate(c) for c in top_chapters],
    )


# ---------------------------------------------------------------------------
# Endpoints: Follow / Unfollow
# ---------------------------------------------------------------------------

@router.post("/follow/{creator_id}", response_model=FollowStatus)
async def follow_creator(
    creator_id: int,
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Follow a creator."""
    # Verify creator exists
    cresult = await session.execute(
        select(CreatorProfile).where(CreatorProfile.id == creator_id)
    )
    creator = cresult.scalar_one_or_none()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    # Check if already following
    existing = await session.execute(
        select(CreatorFollower).where(
            and_(
                CreatorFollower.user_id == user.id,
                CreatorFollower.creator_id == creator_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        return FollowStatus(following=True, follower_count=creator.follower_count or 0)

    follow = CreatorFollower(user_id=user.id, creator_id=creator_id)
    creator.follower_count = (creator.follower_count or 0) + 1
    session.add(follow)
    await session.commit()
    return FollowStatus(following=True, follower_count=creator.follower_count)


@router.delete("/follow/{creator_id}", response_model=FollowStatus)
async def unfollow_creator(
    creator_id: int,
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """Unfollow a creator."""
    result = await session.execute(
        select(CreatorFollower).where(
            and_(
                CreatorFollower.user_id == user.id,
                CreatorFollower.creator_id == creator_id,
            )
        )
    )
    follow = result.scalar_one_or_none()
    if not follow:
        # Also update follower count on creator
        cresult = await session.execute(
            select(CreatorProfile).where(CreatorProfile.id == creator_id)
        )
        creator = cresult.scalar_one_or_none()
        fc = creator.follower_count if creator else 0
        return FollowStatus(following=False, follower_count=fc)

    await session.delete(follow)
    # Decrement follower count
    cresult = await session.execute(
        select(CreatorProfile).where(CreatorProfile.id == creator_id)
    )
    creator = cresult.scalar_one_or_none()
    if creator:
        creator.follower_count = max(0, (creator.follower_count or 1) - 1)
    await session.commit()
    return FollowStatus(following=False, follower_count=creator.follower_count if creator else 0)


@router.get("/followers", response_model=list[int])
async def my_following(
    user=Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
):
    """List creator IDs that the authenticated user follows."""
    result = await session.execute(
        select(CreatorFollower.creator_id).where(CreatorFollower.user_id == user.id)
    )
    return [row[0] for row in result.all()]


# ---------------------------------------------------------------------------
# Endpoints: Public Browse
# ---------------------------------------------------------------------------

@router.get("/browse", response_model=list[CreatorBrowseItem])
async def browse_creators(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Browse all registered creators (public)."""
    result = await session.execute(
        select(CreatorProfile)
        .order_by(desc(CreatorProfile.follower_count))
        .offset(offset)
        .limit(limit)
    )
    profiles = result.scalars().all()
    items = []
    for p in profiles:
        sc = await session.execute(
            select(func.count(CreatorSeries.id)).where(
                CreatorSeries.creator_id == p.id
            )
        )
        series_count = sc.scalar() or 0
        items.append(CreatorBrowseItem(
            id=p.id,
            display_name=p.display_name,
            avatar_url=p.avatar_url,
            bio=p.bio,
            follower_count=p.follower_count or 0,
            series_count=series_count,
            verified=p.verified,
        ))
    return items


@router.get("/browse/{creator_id}")
async def browse_creator_detail(
    creator_id: int,
    session: AsyncSession = Depends(get_session),
):
    """View a creator's public profile and their published series."""
    result = await session.execute(
        select(CreatorProfile).where(CreatorProfile.id == creator_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Creator not found")

    sresult = await session.execute(
        select(CreatorSeries)
        .where(and_(CreatorSeries.creator_id == creator_id, CreatorSeries.published == True))
        .order_by(desc(CreatorSeries.updated_at))
    )
    series = sresult.scalars().all()

    return {
        "profile": ProfileOut.model_validate(profile),
        "series": [SeriesOut.model_validate(s) for s in series],
    }


@router.get("/browse/{creator_id}/series/{series_id}")
async def browse_creator_series(
    creator_id: int,
    series_id: int,
    session: AsyncSession = Depends(get_session),
):
    """View a public series and its published chapters."""
    result = await session.execute(
        select(CreatorSeries).where(
            and_(
                CreatorSeries.id == series_id,
                CreatorSeries.creator_id == creator_id,
                CreatorSeries.published == True,
            )
        )
    )
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    chresult = await session.execute(
        select(CreatorChapter)
        .where(and_(CreatorChapter.series_id == series_id, CreatorChapter.published == True))
        .order_by(CreatorChapter.chapter_number)
    )
    chapters = chresult.scalars().all()

    return {
        "series": SeriesOut.model_validate(series),
        "chapters": [ChapterOut.model_validate(c) for c in chapters],
    }
