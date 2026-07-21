"""Tier 5: recommendations, trending, bookmarks, webhooks."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import Bookmark, WebhookSubscription, get_session
from ..http import fetch_json
from ..schemas import ApiResponse
from ..sources.registry import anime_source, comic_source, novel_source
from ..sources.anilist import _media_to_summary

router = APIRouter(tags=["tier5"])

ContentType = Literal["anime", "comic", "novel"]


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


# ---------------------------------------------------------------------------
# Recommendations + Trending
# ---------------------------------------------------------------------------


@router.get("/recommend/{content_type}", response_model=ApiResponse, summary="Recommendations")
async def recommend(
    content_type: ContentType,
    seed: Optional[str] = Query(None, description="Optional seed title/id"),
    limit: int = Query(12, ge=1, le=30),
):
    """Recommend titles.

    - anime: AniList recommendations (or popular if no seed)
    - comic: MangaDex popular / related-ish via search seed
    - novel: sakuranovel popular fallback
    """
    items: List[dict] = []
    source_name = "unknown"
    try:
        if content_type == "anime":
            source_name = "anilist"
            src = anime_source("anilist")
            if not src:
                raise HTTPException(status_code=500, detail="anilist source missing")
            if seed and seed.isdigit():
                q = (
                    "query($id:Int!){Media(id:$id,type:ANIME){recommendations(perPage:20){"
                    "nodes{mediaRecommendation{id title{romaji english} coverImage{large color} "
                    "episodes status genres averageScore}}}}}"
                )
                data = await src._query(q, {"id": int(seed)})  # type: ignore[attr-defined]
                nodes = (
                    ((data.get("Media") or {}).get("recommendations") or {}).get("nodes") or []
                )
                for n in nodes:
                    m = n.get("mediaRecommendation")
                    if m:
                        items.append(_media_to_summary(m))
            if not items:
                if hasattr(src, "trending"):
                    items = await src.trending()  # type: ignore[attr-defined]
                else:
                    items = await getattr(src, "popular", src.home)()
        elif content_type == "comic":
            source_name = "mangadex"
            src = comic_source("mangadex")
            if not src:
                raise HTTPException(status_code=500, detail="mangadex source missing")
            if seed:
                items = await src.search(seed)
            if not items:
                items = await getattr(src, "popular", src.home)()
        else:
            source_name = "sakuranovel"
            src = novel_source("sakuranovel")
            if not src:
                raise HTTPException(status_code=500, detail="sakuranovel source missing")
            if seed and hasattr(src, "search"):
                items = await src.search(seed)
            if not items:
                if hasattr(src, "popular"):
                    items = await getattr(src, "popular", src.home)()
                else:
                    items = await src.home()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"recommend failed: {e}") from e

    return ApiResponse(
        source=source_name,
        data={"seed": seed, "content_type": content_type, "items": items[:limit]},
    )


@router.get("/trending/{content_type}", response_model=ApiResponse, summary="Trending titles")
async def trending(content_type: ContentType, limit: int = Query(20, ge=1, le=50)):
    items: List[dict] = []
    source_name = "unknown"
    try:
        if content_type == "anime":
            source_name = "anilist"
            src = anime_source("anilist")
            if not src:
                raise HTTPException(status_code=500, detail="anilist source missing")
            if hasattr(src, "trending"):
                items = await src.trending()  # type: ignore[attr-defined]
            else:
                items = await getattr(src, "popular", src.home)()
        elif content_type == "comic":
            source_name = "mangadex"
            src = comic_source("mangadex")
            if not src:
                raise HTTPException(status_code=500, detail="mangadex source missing")
            items = await getattr(src, "popular", src.home)()
        else:
            source_name = "sakuranovel"
            src = novel_source("sakuranovel")
            if not src:
                raise HTTPException(status_code=500, detail="sakuranovel source missing")
            items = await (src.popular() if hasattr(src, "popular") else src.home())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"trending failed: {e}") from e
    return ApiResponse(
        source=source_name,
        data={"content_type": content_type, "items": items[:limit]},
    )


# ---------------------------------------------------------------------------
# Bookmarks
# ---------------------------------------------------------------------------


class BookmarkCreate(BaseModel):
    source: str = Field(..., min_length=1, max_length=64)
    content_id: str = Field(..., min_length=1, max_length=128)
    content_type: ContentType
    title: Optional[str] = Field(None, max_length=255)
    thumbnail: Optional[str] = Field(None, max_length=512)
    note: Optional[str] = None


class BookmarkOut(BaseModel):
    id: int
    user_id: int
    source: str
    content_id: str
    content_type: str
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime


@router.post("/bookmarks", response_model=ApiResponse, status_code=201)
async def create_bookmark(
    body: BookmarkCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    uid = _require_user(request)
    existing = (
        await session.execute(
            select(Bookmark).where(
                Bookmark.user_id == uid,
                Bookmark.source == body.source,
                Bookmark.content_id == body.content_id,
                Bookmark.content_type == body.content_type,
            )
        )
    ).scalar_one_or_none()
    if existing:
        # update metadata
        existing.title = body.title or existing.title
        existing.thumbnail = body.thumbnail or existing.thumbnail
        existing.note = body.note if body.note is not None else existing.note
        await session.commit()
        await session.refresh(existing)
        row = existing
    else:
        row = Bookmark(
            user_id=uid,
            source=body.source,
            content_id=body.content_id,
            content_type=body.content_type,
            title=body.title,
            thumbnail=body.thumbnail,
            note=body.note,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return ApiResponse(
        data=BookmarkOut(
            id=row.id,
            user_id=row.user_id,
            source=row.source,
            content_id=row.content_id,
            content_type=row.content_type,
            title=row.title,
            thumbnail=row.thumbnail,
            note=row.note,
            created_at=row.created_at,
        ).model_dump()
    )


@router.get("/bookmarks", response_model=ApiResponse)
async def list_bookmarks(
    request: Request,
    content_type: Optional[ContentType] = None,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    uid = _require_user(request)
    stmt = (
        select(Bookmark)
        .where(Bookmark.user_id == uid)
        .order_by(Bookmark.created_at.desc())
        .limit(limit)
    )
    if content_type:
        stmt = stmt.where(Bookmark.content_type == content_type)
    rows = (await session.execute(stmt)).scalars().all()
    return ApiResponse(
        data=[
            BookmarkOut(
                id=r.id,
                user_id=r.user_id,
                source=r.source,
                content_id=r.content_id,
                content_type=r.content_type,
                title=r.title,
                thumbnail=r.thumbnail,
                note=r.note,
                created_at=r.created_at,
            ).model_dump()
            for r in rows
        ]
    )


@router.delete("/bookmarks/{bookmark_id}", response_model=ApiResponse)
async def delete_bookmark(
    bookmark_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    uid = _require_user(request)
    row = (
        await session.execute(
            select(Bookmark).where(Bookmark.id == bookmark_id, Bookmark.user_id == uid)
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="bookmark not found")
    await session.delete(row)
    await session.commit()
    return ApiResponse(data={"deleted": bookmark_id})


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


class WebhookCreate(BaseModel):
    url: str = Field(..., min_length=8, max_length=512)
    source: Optional[str] = Field(None, max_length=64)
    content_type: Optional[ContentType] = None
    secret: Optional[str] = Field(None, max_length=128)


class WebhookOut(BaseModel):
    id: int
    user_id: int
    url: str
    source: Optional[str] = None
    content_type: Optional[str] = None
    active: bool
    has_secret: bool
    created_at: datetime


@router.post("/webhooks", response_model=ApiResponse, status_code=201)
async def create_webhook(
    body: WebhookCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    uid = _require_user(request)
    if not (body.url.startswith("https://") or body.url.startswith("http://")):
        raise HTTPException(status_code=400, detail="url must be http(s)")
    secret = body.secret or secrets.token_urlsafe(16)
    row = WebhookSubscription(
        user_id=uid,
        url=body.url,
        secret=secret,
        source=body.source,
        content_type=body.content_type,
        active=True,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return ApiResponse(
        data={
            **WebhookOut(
                id=row.id,
                user_id=row.user_id,
                url=row.url,
                source=row.source,
                content_type=row.content_type,
                active=row.active,
                has_secret=True,
                created_at=row.created_at,
            ).model_dump(),
            "secret": secret,  # shown once
        }
    )


@router.get("/webhooks", response_model=ApiResponse)
async def list_webhooks(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    uid = _require_user(request)
    rows = (
        await session.execute(
            select(WebhookSubscription)
            .where(WebhookSubscription.user_id == uid)
            .order_by(WebhookSubscription.created_at.desc())
        )
    ).scalars().all()
    return ApiResponse(
        data=[
            WebhookOut(
                id=r.id,
                user_id=r.user_id,
                url=r.url,
                source=r.source,
                content_type=r.content_type,
                active=r.active,
                has_secret=bool(r.secret),
                created_at=r.created_at,
            ).model_dump()
            for r in rows
        ]
    )


@router.delete("/webhooks/{webhook_id}", response_model=ApiResponse)
async def delete_webhook(
    webhook_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    uid = _require_user(request)
    row = (
        await session.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.id == webhook_id,
                WebhookSubscription.user_id == uid,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="webhook not found")
    await session.delete(row)
    await session.commit()
    return ApiResponse(data={"deleted": webhook_id})


@router.post("/webhooks/test/{webhook_id}", response_model=ApiResponse)
async def test_webhook(
    webhook_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Fire a sample event to the registered URL (HMAC signed if secret set)."""
    uid = _require_user(request)
    row = (
        await session.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.id == webhook_id,
                WebhookSubscription.user_id == uid,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="webhook not found")

    payload = {
        "event": "chapter.updated",
        "test": True,
        "source": row.source or "demo",
        "content_type": row.content_type or "comic",
        "content_id": "demo-slug",
        "chapter_id": "ch-1",
        "title": "Nakama webhook test",
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {"Content-Type": "application/json", "X-Nakama-Event": "chapter.updated"}
    if row.secret:
        sig = hmac.new(row.secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-Nakama-Signature"] = f"sha256={sig}"

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(row.url, content=body, headers=headers)
        return ApiResponse(
            data={
                "delivered": resp.status_code < 500,
                "status_code": resp.status_code,
                "url": row.url,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"delivery failed: {e}") from e
