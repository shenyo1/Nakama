"""Community endpoints: reviews, comments, reading lists, and activity feed.

POST/GET /reviews/{source}/{slug}   — submit & get reviews
POST/GET /comments/{source}/{slug}  — submit & get comments (threaded)
POST/GET/PUT/DELETE /lists          — CRUD reading lists
GET /community/feed                 — recent activity
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_session
from ..community_models import Review, Comment, ReadingList, ReadingListItem
from ..ratelimit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["community"])

ContentKind = Literal["anime", "comic", "novel"]


# ── Helper functions (must be defined before endpoint handlers) ──────────────

def _comment_to_out(row: Comment, username: str = "", replies: list[CommentOut] | None = None) -> CommentOut:
    return CommentOut(
        id=row.id,
        user_id=row.user_id,
        username=username,
        source=row.source,
        slug=row.slug,
        kind=row.kind,
        body=row.body,
        parent_id=row.parent_id,
        created_at=row.created_at,
        replies=replies or [],
    )


# ── Endpoint handlers ────────────────────────────────────────────────────────


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ReviewCreate(BaseModel):
    kind: ContentKind = Field(..., examples=["comic"])
    rating: int = Field(..., ge=1, le=5, examples=[4])
    body: str = Field(..., min_length=1, max_length=5000, examples=["Great read!"])


class ReviewOut(BaseModel):
    id: int
    user_id: int
    username: str = ""
    source: str
    slug: str
    kind: str
    rating: int
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewAggregate(BaseModel):
    """Summary stats for reviews of a single item."""
    count: int
    avg_rating: float
    distribution: dict[int, int]  # {1: N, 2: N, ...}


class CommentCreate(BaseModel):
    kind: ContentKind = Field(..., examples=["comic"])
    body: str = Field(..., min_length=1, max_length=3000)
    parent_id: Optional[int] = Field(None, description="Reply to an existing comment")


class CommentOut(BaseModel):
    id: int
    user_id: int
    username: str = ""
    source: str
    slug: str
    kind: str
    body: str
    parent_id: Optional[int] = None
    created_at: datetime
    replies: list["CommentOut"] = []

    model_config = {"from_attributes": True}


class ReadingListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    is_public: bool = False


class ReadingListUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    is_public: Optional[bool] = None


class ReadingListItemCreate(BaseModel):
    source: str = Field(..., min_length=1, max_length=64)
    slug: str = Field(..., min_length=1, max_length=256)
    kind: ContentKind


class ReadingListItemOut(BaseModel):
    id: int
    source: str
    slug: str
    kind: str
    added_at: datetime

    model_config = {"from_attributes": True}


class ReadingListOut(BaseModel):
    id: int
    user_id: int
    username: str = ""
    name: str
    is_public: bool
    created_at: datetime
    items: list[ReadingListItemOut] = []

    model_config = {"from_attributes": True}


class FeedItem(BaseModel):
    type: Literal["review", "comment", "list"]
    user_id: int
    username: str = ""
    data: dict
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


async def _get_username(session: AsyncSession, user_id: int) -> str:
    from ..db import User
    row = (await session.execute(select(User.username).where(User.id == user_id))).scalar_one_or_none()
    return row if row else ""


def _review_to_out(row: Review, username: str = "") -> ReviewOut:
    return ReviewOut(
        id=row.id,
        user_id=row.user_id,
        username=username,
        source=row.source,
        slug=row.slug,
        kind=row.kind,
        rating=row.rating,
        body=row.body,
        created_at=row.created_at,
    )


# ---------------------------------------------------------------------------
# REVIEWS
# ---------------------------------------------------------------------------


@router.post(
    "/reviews/{source}/{slug:path}",
    response_model=ReviewOut,
    status_code=201,
    summary="Submit a review for content",
)
@limiter.limit("10/minute")
async def create_review(
    source: str,
    slug: str,
    payload: ReviewCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ReviewOut:
    uid = _jwt_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    # One review per user per item.
    existing = (
        await session.execute(
            select(Review).where(
                Review.user_id == uid,
                Review.source == source,
                Review.slug == slug,
                Review.kind == payload.kind,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="You have already reviewed this item")

    row = Review(
        user_id=uid,
        source=source,
        slug=slug,
        kind=payload.kind,
        rating=payload.rating,
        body=payload.body,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    username = await _get_username(session, uid)
    return _review_to_out(row, username)


@router.get(
    "/reviews/{source}/{slug:path}",
    response_model=List[ReviewOut],
    summary="Get reviews for content",
)
async def get_reviews(
    source: str,
    slug: str,
    kind: Optional[ContentKind] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> List[ReviewOut]:
    stmt = select(Review).where(Review.source == source, Review.slug == slug)
    if kind:
        stmt = stmt.where(Review.kind == kind)
    stmt = stmt.order_by(desc(Review.created_at)).offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(stmt)
    rows = result.scalars().all()

    # Batch-fetch usernames.
    user_ids = list({r.user_id for r in rows})
    username_map: dict[int, str] = {}
    if user_ids:
        from ..db import User
        user_rows = (await session.execute(
            select(User.id, User.username).where(User.id.in_(user_ids))
        )).all()
        username_map = {uid: uname for uid, uname in user_rows}

    return [
        _review_to_out(r, username_map.get(r.user_id, ""))
        for r in rows
    ]


@router.get(
    "/reviews/{source}/{slug:path}/stats",
    response_model=ReviewAggregate,
    summary="Get review stats for content",
)
async def get_review_stats(
    source: str,
    slug: str,
    kind: Optional[ContentKind] = Query(None),
    session: AsyncSession = Depends(get_session),
) -> ReviewAggregate:
    stmt = select(Review.rating).where(Review.source == source, Review.slug == slug)
    if kind:
        stmt = stmt.where(Review.kind == kind)

    result = await session.execute(stmt)
    ratings = result.scalars().all()

    if not ratings:
        return ReviewAggregate(count=0, avg_rating=0.0, distribution={i: 0 for i in range(1, 6)})

    dist: dict[int, int] = {i: 0 for i in range(1, 6)}
    for r in ratings:
        dist[r] = dist.get(r, 0) + 1

    return ReviewAggregate(
        count=len(ratings),
        avg_rating=round(sum(ratings) / len(ratings), 2),
        distribution=dist,
    )


# ---------------------------------------------------------------------------
# COMMENTS
# ---------------------------------------------------------------------------


@router.post(
    "/comments/{source}/{slug:path}",
    response_model=CommentOut,
    status_code=201,
    summary="Post a comment on content",
)
@limiter.limit("20/minute")
async def create_comment(
    source: str,
    slug: str,
    payload: CommentCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> CommentOut:
    uid = _jwt_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Validate parent_id if provided.
    if payload.parent_id is not None:
        parent = (await session.execute(
            select(Comment).where(Comment.id == payload.parent_id)
        )).scalar_one_or_none()
        if parent is None:
            raise HTTPException(status_code=404, detail="Parent comment not found")

    row = Comment(
        user_id=uid,
        source=source,
        slug=slug,
        kind=payload.kind,
        body=payload.body,
        parent_id=payload.parent_id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)

    username = await _get_username(session, uid)
    return _comment_to_out(row, username)


@router.get(
    "/comments/{source}/{slug:path}",
    response_model=List[CommentOut],
    summary="Get threaded comments for content",
)
async def get_comments(
    source: str,
    slug: str,
    kind: Optional[ContentKind] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> List[CommentOut]:
    # Fetch top-level comments.
    stmt = (
        select(Comment)
        .where(Comment.source == source, Comment.slug == slug, Comment.parent_id.is_(None))
    )
    if kind:
        stmt = stmt.where(Comment.kind == kind)
    stmt = stmt.order_by(desc(Comment.created_at)).offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(stmt)
    top_rows = result.scalars().all()

    # Fetch all replies for these top-level comments.
    top_ids = [r.id for r in top_rows]
    reply_rows: list[Comment] = []
    if top_ids:
        reply_result = await session.execute(
            select(Comment)
            .where(Comment.parent_id.in_(top_ids))
            .order_by(Comment.created_at)
        )
        reply_rows = list(reply_result.scalars().all())

    # Collect all user_ids.
    all_user_ids = {r.user_id for r in top_rows} | {r.user_id for r in reply_rows}
    username_map: dict[int, str] = {}
    if all_user_ids:
        from ..db import User
        user_rows = (await session.execute(
            select(User.id, User.username).where(User.id.in_(list(all_user_ids)))
        )).all()
        username_map = {uid: uname for uid, uname in user_rows}

    # Build reply map.
    reply_map: dict[int, list[Comment]] = {}
    for r in reply_rows:
        reply_map.setdefault(r.parent_id, []).append(r)

    return [
        _comment_to_out(
            top,
            username_map.get(top.user_id, ""),
            [
                _comment_to_out(r, username_map.get(r.user_id, ""))
                for r in reply_map.get(top.id, [])
            ],
        )
        for top in top_rows
    ]


# ---------------------------------------------------------------------------
# READING LISTS
# ---------------------------------------------------------------------------


@router.post(
    "/lists",
    response_model=ReadingListOut,
    status_code=201,
    summary="Create a reading list",
)
@limiter.limit("10/minute")
async def create_list(
    payload: ReadingListCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ReadingListOut:
    uid = _jwt_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    row = ReadingList(user_id=uid, name=payload.name, is_public=payload.is_public)
    session.add(row)
    await session.commit()
    await session.refresh(row)

    username = await _get_username(session, uid)
    return ReadingListOut(
        id=row.id,
        user_id=row.user_id,
        username=username,
        name=row.name,
        is_public=row.is_public,
        created_at=row.created_at,
        items=[],
    )


@router.get(
    "/lists",
    response_model=List[ReadingListOut],
    summary="List reading lists for the current user",
)
async def get_lists(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> List[ReadingListOut]:
    uid = _jwt_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    rows = (
        await session.execute(
            select(ReadingList)
            .where(ReadingList.user_id == uid)
            .options(selectinload(ReadingList.items))
            .order_by(desc(ReadingList.created_at))
        )
    ).scalars().unique().all()

    username = await _get_username(session, uid)
    return [_list_to_out(r, username) for r in rows]


@router.get(
    "/lists/{list_id}",
    response_model=ReadingListOut,
    summary="Get a single reading list",
)
async def get_list(
    list_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ReadingListOut:
    uid = _jwt_user_id(request)

    row = (
        await session.execute(
            select(ReadingList)
            .where(ReadingList.id == list_id)
            .options(selectinload(ReadingList.items))
        )
    ).scalar_one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="List not found")
    if not row.is_public and (uid is None or row.user_id != uid):
        raise HTTPException(status_code=403, detail="This list is private")

    username = await _get_username(session, row.user_id)
    return _list_to_out(row, username)


@router.put(
    "/lists/{list_id}",
    response_model=ReadingListOut,
    summary="Update a reading list",
)
async def update_list(
    list_id: int,
    payload: ReadingListUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ReadingListOut:
    uid = _jwt_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    row = (
        await session.execute(
            select(ReadingList)
            .where(ReadingList.id == list_id, ReadingList.user_id == uid)
            .options(selectinload(ReadingList.items))
        )
    ).scalar_one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="List not found")

    if payload.name is not None:
        row.name = payload.name
    if payload.is_public is not None:
        row.is_public = payload.is_public

    await session.commit()
    await session.refresh(row)

    username = await _get_username(session, uid)
    return _list_to_out(row, username)


@router.delete(
    "/lists/{list_id}",
    status_code=204,
    summary="Delete a reading list",
)
async def delete_list(
    list_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    uid = _jwt_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    row = (
        await session.execute(
            select(ReadingList).where(
                ReadingList.id == list_id, ReadingList.user_id == uid
            )
        )
    ).scalar_one_or_none()

    if row is None:
        raise HTTPException(status_code=404, detail="List not found")

    await session.delete(row)
    await session.commit()


@router.post(
    "/lists/{list_id}/items",
    response_model=ReadingListItemOut,
    status_code=201,
    summary="Add an item to a reading list",
)
@limiter.limit("30/minute")
async def add_list_item(
    list_id: int,
    payload: ReadingListItemCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ReadingListItemOut:
    uid = _jwt_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Verify ownership.
    lst = (
        await session.execute(
            select(ReadingList).where(
                ReadingList.id == list_id, ReadingList.user_id == uid
            )
        )
    ).scalar_one_or_none()
    if lst is None:
        raise HTTPException(status_code=404, detail="List not found")

    # Check for duplicates.
    existing = (
        await session.execute(
            select(ReadingListItem).where(
                ReadingListItem.list_id == list_id,
                ReadingListItem.source == payload.source,
                ReadingListItem.slug == payload.slug,
                ReadingListItem.kind == payload.kind,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Item already in list")

    item = ReadingListItem(
        list_id=list_id,
        source=payload.source,
        slug=payload.slug,
        kind=payload.kind,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)

    return ReadingListItemOut(
        id=item.id,
        source=item.source,
        slug=item.slug,
        kind=item.kind,
        added_at=item.added_at,
    )


@router.delete(
    "/lists/{list_id}/items/{item_id}",
    status_code=204,
    summary="Remove an item from a reading list",
)
async def remove_list_item(
    list_id: int,
    item_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    uid = _jwt_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Verify ownership.
    lst = (
        await session.execute(
            select(ReadingList).where(
                ReadingList.id == list_id, ReadingList.user_id == uid
            )
        )
    ).scalar_one_or_none()
    if lst is None:
        raise HTTPException(status_code=404, detail="List not found")

    item = (
        await session.execute(
            select(ReadingListItem).where(
                ReadingListItem.id == item_id, ReadingListItem.list_id == list_id
            )
        )
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    await session.delete(item)
    await session.commit()


# ---------------------------------------------------------------------------
# COMMUNITY FEED
# ---------------------------------------------------------------------------


@router.get(
    "/community/feed",
    response_model=List[FeedItem],
    summary="Recent community activity feed",
)
async def community_feed(
    limit: int = Query(20, ge=1, le=100),
    kind: Optional[ContentKind] = Query(None),
    session: AsyncSession = Depends(get_session),
) -> List[FeedItem]:
    """Returns the most recent reviews, comments, and public list creations.

    Results are merged and sorted by creation time, newest first.
    """
    from ..db import User

    feed: list[FeedItem] = []

    # Recent reviews.
    review_stmt = select(Review)
    if kind:
        review_stmt = review_stmt.where(Review.kind == kind)
    review_stmt = review_stmt.order_by(desc(Review.created_at)).limit(limit)
    review_rows = (await session.execute(review_stmt)).scalars().all()

    # Recent comments.
    comment_stmt = select(Comment)
    if kind:
        comment_stmt = comment_stmt.where(Comment.kind == kind)
    comment_stmt = comment_stmt.order_by(desc(Comment.created_at)).limit(limit)
    comment_rows = (await session.execute(comment_stmt)).scalars().all()

    # Recent public lists.
    list_stmt = (
        select(ReadingList)
        .where(ReadingList.is_public.is_(True))
        .order_by(desc(ReadingList.created_at))
        .limit(limit)
    )
    list_rows = (await session.execute(list_stmt)).scalars().all()

    # Batch usernames.
    all_user_ids = (
        {r.user_id for r in review_rows}
        | {c.user_id for c in comment_rows}
        | {l.user_id for l in list_rows}
    )
    username_map: dict[int, str] = {}
    if all_user_ids:
        user_rows = (await session.execute(
            select(User.id, User.username).where(User.id.in_(list(all_user_ids)))
        )).all()
        username_map = {uid: uname for uid, uname in user_rows}

    for r in review_rows:
        feed.append(FeedItem(
            type="review",
            user_id=r.user_id,
            username=username_map.get(r.user_id, ""),
            data={"source": r.source, "slug": r.slug, "kind": r.kind, "rating": r.rating, "body": r.body[:200]},
            created_at=r.created_at,
        ))

    for c in comment_rows:
        feed.append(FeedItem(
            type="comment",
            user_id=c.user_id,
            username=username_map.get(c.user_id, ""),
            data={"source": c.source, "slug": c.slug, "kind": c.kind, "body": c.body[:200]},
            created_at=c.created_at,
        ))

    for l in list_rows:
        feed.append(FeedItem(
            type="list",
            user_id=l.user_id,
            username=username_map.get(l.user_id, ""),
            data={"list_id": l.id, "name": l.name},
            created_at=l.created_at,
        ))

    # Merge and sort by created_at descending.
    feed.sort(key=lambda x: x.created_at, reverse=True)
    return feed[:limit]


def _list_to_out(row: ReadingList, username: str = "") -> ReadingListOut:
    return ReadingListOut(
        id=row.id,
        user_id=row.user_id,
        username=username,
        name=row.name,
        is_public=row.is_public,
        created_at=row.created_at,
        items=[
            ReadingListItemOut(
                id=it.id,
                source=it.source,
                slug=it.slug,
                kind=it.kind,
                added_at=it.added_at,
            )
            for it in (row.items or [])
        ],
    )
