"""Reading-history endpoints: POST/GET /history.

These are intentionally unauthenticated for now — same posture as the rest
of the API (auth is opt-in via ``API_KEY`` env var, and only the data
sources are gated). When real user accounts land, the ``user_id`` body field
will be derived from the authenticated session instead of trusted from the
client.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import ReadingHistory, get_session


router = APIRouter(tags=["history"])

ContentType = Literal["anime", "comic", "novel"]


class HistoryCreate(BaseModel):
    """Body schema for POST /history."""

    user_id: int = Field(..., ge=1, description="Numeric user id (FK to users.id)")
    source: str = Field(..., min_length=1, max_length=64, examples=["otakudesu"])
    content_id: str = Field(..., min_length=1, max_length=128, examples=["boruto"])
    content_type: ContentType = Field(..., examples=["anime"])
    chapter_id: str = Field(..., min_length=1, max_length=128, examples=["episode-1"])


class HistoryEntry(BaseModel):
    """Response shape for a single reading-history row."""

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


@router.post(
    "/history",
    response_model=HistoryEntry,
    status_code=201,
    summary="Record a reading event",
)
async def post_history(
    payload: HistoryCreate,
    session: AsyncSession = Depends(get_session),
) -> HistoryEntry:
    """Insert a new reading-history row and return it."""
    row = ReadingHistory(
        user_id=payload.user_id,
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
    user_id: int = Query(..., ge=1, description="Numeric user id"),
    content_type: Optional[ContentType] = Query(
        None, description="Filter by content type (anime/comic/novel)"
    ),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[HistoryEntry]:
    """Return up to ``limit`` history rows for ``user_id``, newest first.

    Optional ``content_type`` filter narrows to a single medium.
    """
    stmt = (
        select(ReadingHistory)
        .where(ReadingHistory.user_id == user_id)
        .order_by(ReadingHistory.read_at.desc(), ReadingHistory.id.desc())
        .limit(limit)
    )
    if content_type is not None:
        stmt = stmt.where(ReadingHistory.content_type == content_type)

    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [_to_entry(r) for r in rows]


# Guard so HEAD/OPTIONS etc. don't blow up if anyone hits the path bare.
@router.get("/history/", include_in_schema=False)
async def _history_index() -> dict:
    raise HTTPException(
        status_code=400,
        detail="GET /history requires ?user_id=<int>. Use POST /history to record.",
    )
