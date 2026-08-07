"""Gamification & social router — Fase 4 (learnings from Sanka/Lovable).

Endpoints (registered under the public ``/social`` prefix so any reader can
view the leaderboard & activity without auth; mutating club actions require a
JWT user):

* ``GET  /social/leaderboard``        — weekly top readers (XP, streak, level)
* ``GET  /social/activity``           — social activity feed (optionally by user)
* ``GET  /social/stats/{user_id}``    — one user's gamification stats
* ``GET  /social/clubs``              — list reading clubs (search by name)
* ``POST /social/clubs``              — create a club (JWT)
* ``POST /social/clubs/{id}/join``    — join a club (JWT)
* ``POST /social/clubs/{id}/leave``   — leave a club (JWT)
* ``POST /social/clubs/{id}/posts``   — post to a club (JWT)
* ``GET  /social/clubs/{id}``         — club detail + posts + member count
"""
from __future__ import annotations

import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import gamification
from ..db import get_session
from ..gamification_models import ReadingClub, ReadingClubMember, ReadingClubPost
from ..schemas import ApiResponse

router = APIRouter(prefix="/social", tags=["social"])


def _jwt_user_id(request: Request) -> Optional[int]:
    """Resolve the authenticated user id for public-route club mutations.

    The global API-key middleware only sets ``auth_principal`` for *metered*
    routes; `/social/*` is public so we must decode the Bearer JWT ourselves
    when present. Returns None for anon / invalid / missing token.
    """
    principal = getattr(request.state, "auth_principal", None) or ""
    if principal.startswith("user:"):
        try:
            return int(principal.split(":", 1)[1])
        except ValueError:
            return None
    # Public route: parse the Authorization header directly.
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        try:
            from ..security import decode_token

            data = decode_token(token, expected_type="access")
            sub = data.get("sub")
            if sub is not None:
                return int(sub)
        except Exception:
            return None
    return None


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:32] or "club"
    return f"{base}-{uuid.uuid4().hex[:6]}"


# --- Request models ---


class ClubCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    description: Optional[str] = Field(None, max_length=2000)
    content_type: Optional[str] = Field(None, pattern=r"^(anime|comic|novel)$")
    source: Optional[str] = Field(None, max_length=64)
    content_id: Optional[str] = Field(None, max_length=128)
    is_public: bool = True


class ClubPostCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


# --- Leaderboard & activity ---


@router.get("/leaderboard", response_model=ApiResponse)
async def leaderboard(
    request: Request,
    limit: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    rows = await gamification.weekly_leaderboard(session, limit)
    return ApiResponse(
        source="social",
        data={"items": rows, "total": len(rows), "period": "last-7-days"},
    )


@router.get("/activity", response_model=ApiResponse)
async def activity(
    request: Request,
    user_id: Optional[int] = Query(None, ge=1, description="Filter to one user"),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    rows = await gamification.activity_feed(session, user_id=user_id, limit=limit)
    return ApiResponse(source="social", data={"items": rows, "total": len(rows)})


@router.get("/stats/{user_id}", response_model=ApiResponse)
async def stats(
    user_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    data = await gamification.user_stats(session, user_id)
    return ApiResponse(source="social", data=data)


# --- Clubs ---


@router.get("/clubs", response_model=ApiResponse)
async def list_clubs(
    request: Request,
    q: Optional[str] = Query(None, description="Search clubs by name"),
    content_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(ReadingClub).order_by(ReadingClub.created_at.desc()).limit(limit)
    if q:
        stmt = stmt.where(ReadingClub.name.ilike(f"%{q}%"))
    if content_type:
        stmt = stmt.where(ReadingClub.content_type == content_type)
    rows = (await session.execute(stmt)).scalars().all()

    items = []
    for c in rows:
        cnt = (
            await session.execute(
                select(func.count()).select_from(ReadingClubMember).where(ReadingClubMember.club_id == c.id)
            )
        ).scalar() or 0
        items.append(
            {
                "id": c.id,
                "slug": c.slug,
                "name": c.name,
                "description": c.description,
                "owner_id": c.owner_id,
                "content_type": c.content_type,
                "source": c.source,
                "content_id": c.content_id,
                "is_public": c.is_public,
                "member_count": cnt,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
        )
    return ApiResponse(source="social", data={"items": items, "total": len(items)})


@router.post("/clubs", response_model=ApiResponse, status_code=201)
async def create_club(
    body: ClubCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    uid = _jwt_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="JWT required to create a club")
    club = ReadingClub(
        slug=_slugify(body.name),
        name=body.name,
        description=body.description,
        owner_id=uid,
        content_type=body.content_type,
        source=body.source,
        content_id=body.content_id,
        is_public=body.is_public,
    )
    session.add(club)
    await session.flush()
    member = ReadingClubMember(club_id=club.id, user_id=uid, role="owner")
    session.add(member)
    await session.commit()
    await session.refresh(club)
    await gamification.record_activity(
        session, uid, "create_club", content_type=body.content_type, title=body.name
    )
    return ApiResponse(
        source="social",
        data={"id": club.id, "slug": club.slug, "name": club.name},
    )


async def _club_or_404(session: AsyncSession, club_id: int) -> ReadingClub:
    club = (
        await session.execute(select(ReadingClub).where(ReadingClub.id == club_id))
    ).scalar_one_or_none()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    return club


@router.post("/clubs/{club_id}/join", response_model=ApiResponse)
async def join_club(
    club_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    uid = _jwt_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="JWT required")
    club = await _club_or_404(session, club_id)
    exists = (
        await session.execute(
            select(ReadingClubMember).where(
                ReadingClubMember.club_id == club_id,
                ReadingClubMember.user_id == uid,
            )
        )
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Already a member")
    session.add(ReadingClubMember(club_id=club_id, user_id=uid, role="member"))
    await session.commit()
    await gamification.record_activity(
        session, uid, "join_club", content_type=club.content_type, title=club.name
    )
    return ApiResponse(source="social", data={"joined": True, "club_id": club_id})


@router.post("/clubs/{club_id}/leave", response_model=ApiResponse)
async def leave_club(
    club_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    uid = _jwt_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="JWT required")
    await _club_or_404(session, club_id)
    row = (
        await session.execute(
            select(ReadingClubMember).where(
                ReadingClubMember.club_id == club_id,
                ReadingClubMember.user_id == uid,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=409, detail="Not a member")
    await session.delete(row)
    await session.commit()
    return ApiResponse(source="social", data={"left": True, "club_id": club_id})


@router.post("/clubs/{club_id}/posts", response_model=ApiResponse, status_code=201)
async def create_club_post(
    club_id: int,
    body: ClubPostCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    uid = _jwt_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="JWT required")
    await _club_or_404(session, club_id)
    row = ReadingClubPost(club_id=club_id, user_id=uid, content=body.content)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return ApiResponse(source="social", data={"id": row.id, "created_at": row.created_at.isoformat()})


@router.get("/clubs/{club_id}", response_model=ApiResponse)
async def club_detail(
    club_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    club = await _club_or_404(session, club_id)
    cnt = (
        await session.execute(
            select(func.count()).select_from(ReadingClubMember).where(ReadingClubMember.club_id == club_id)
        )
    ).scalar() or 0
    posts = (
        await session.execute(
            select(ReadingClubPost).where(ReadingClubPost.club_id == club_id).order_by(ReadingClubPost.created_at.desc()).limit(50)
        )
    ).scalars().all()
    return ApiResponse(
        source="social",
        data={
            "id": club.id,
            "slug": club.slug,
            "name": club.name,
            "description": club.description,
            "owner_id": club.owner_id,
            "content_type": club.content_type,
            "is_public": club.is_public,
            "member_count": cnt,
            "posts": [
                {
                    "id": p.id,
                    "user_id": p.user_id,
                    "content": p.content,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in posts
            ],
            "created_at": club.created_at.isoformat() if club.created_at else None,
        },
    )
