"""Reading-history endpoints: POST/GET /history (JWT-aware)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import ReadingHistory, get_session


router = APIRouter(tags=["history"])

ContentType = Literal["anime", "comic", "novel"]


class HistoryCreate(BaseModel):
    """Body schema for POST /history."""

    source: str = Field(..., min_length=1, max_length=64, examples=["otakudesu"])
    content_id: str = Field(..., min_length=1, max_length=128, examples=["boruto"])
    content_type: ContentType = Field(..., examples=["anime"])
    chapter_id: str = Field(..., min_length=1, max_length=128, examples=["episode-1"])
    # Optional when using service API key; required/overridden for JWT users.
    user_id: Optional[int] = Field(None, ge=1, description="Only for service API key callers")


class HistoryEntry(BaseModel):
    id: int
    user_id: int
    source: str
    content_id: str
    content_type: str
    chapter_id: str
    read_at: datetime


def _to_entry(row: ReadingHistory) -> HistoryEntry:
    return HistoryEntry(
        id=row.id,
        user_id=row.user_id,
        source=row.source,
        content_id=row.content_id,
        content_type=row.content_type,
        chapter_id=row.chapter_id,
        read_at=row.read_at,
    )


def _jwt_user_id(request: Request) -> Optional[int]:
    principal = getattr(request.state, "auth_principal", None) or ""
    if principal.startswith("user:"):
        try:
            return int(principal.split(":", 1)[1])
        except ValueError:
            return None
    return None


@router.post(
    "/history",
    response_model=HistoryEntry,
    status_code=201,
    summary="Record a reading event",
)
async def post_history(
    payload: HistoryCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> HistoryEntry:
    uid = _jwt_user_id(request)
    if uid is None:
        if payload.user_id is None:
            raise HTTPException(status_code=400, detail="user_id required without JWT")
        uid = payload.user_id
    row = ReadingHistory(
        user_id=uid,
        source=payload.source,
        content_id=payload.content_id,
        content_type=payload.content_type,
        chapter_id=payload.chapter_id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_entry(row)


@router.get(
    "/history",
    response_model=list[HistoryEntry],
    summary="List reading history for a user",
)
async def get_history(
    request: Request,
    user_id: Optional[int] = Query(None, ge=1, description="Numeric user id (service key only)"),
    content_type: Optional[ContentType] = Query(
        None, description="Filter by content type (anime/comic/novel)"
    ),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[HistoryEntry]:
    uid = _jwt_user_id(request)
    if uid is None:
        if user_id is None:
            raise HTTPException(status_code=400, detail="user_id required without JWT")
        uid = user_id
    stmt = (
        select(ReadingHistory)
        .where(ReadingHistory.user_id == uid)
        .order_by(ReadingHistory.read_at.desc(), ReadingHistory.id.desc())
        .limit(limit)
    )
    if content_type is not None:
        stmt = stmt.where(ReadingHistory.content_type == content_type)

    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [_to_entry(r) for r in rows]
