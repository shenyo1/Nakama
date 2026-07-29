"""
Trending analytics router — tracks and exposes what's popular across all sources.

Endpoints:
  GET  /trending          — top items by recent views/searches
  GET  /trending/{kind}   — top items for specific kind (anime/comic/novel)
  GET  /popular/{kind}    — all-time popular (by total access count)
  
Data is stored in Redis with per-item counters and decay for trending window.
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter, Query

from ..ratelimit import limiter
from ..config import get_settings

router = APIRouter(prefix="/trending", tags=["Trending"])

# Time window for trending (seconds)
TRENDING_WINDOW = 3600 * 24  # 24 hours
POPULAR_WINDOW = 3600 * 24 * 30  # 30 days


def _redis_key(kind: str, slug: str, window: str = "trending") -> str:
    """Build Redis key for trending counters."""
    return f"nakama:{window}:{kind}:{slug}"


async def _get_top(
    kind: str,
    limit: int = 20,
    window: str = "trending",
) -> list[dict]:
    """Get top items from Redis sorted by access count."""
    import redis.asyncio as redis

    settings = get_settings()
    redis_url = getattr(settings, "redis_url", None) or "redis://localhost:6379"
    
    try:
        r = redis.from_url(redis_url, decode_responses=True)
        pattern = f"nakama:{window}:{kind}:*"
        keys = []
        async for key in r.scan_iter(match=pattern, count=100):
            keys.append(key)
        
        if not keys:
            return []
        
        # Get all values
        pipe = r.pipeline()
        for key in keys:
            pipe.get(key)
            pipe.ttl(key)
        results = await pipe.execute()
        
        items = []
        for i, key in enumerate(keys):
            count = int(results[i * 2] or 0)
            ttl = results[i * 2 + 1] or 0
            slug = key.split(":")[-1]
            items.append({
                "slug": slug,
                "kind": kind,
                "count": count,
                "ttl_seconds": ttl,
            })
        
        items.sort(key=lambda x: x["count"], reverse=True)
        return items[:limit]
    except Exception:
        return []


async def _increment(kind: str, slug: str) -> None:
    """Increment access counter for a trending item."""
    import redis.asyncio as redis

    settings = get_settings()
    redis_url = getattr(settings, "redis_url", None) or "redis://localhost:6379"
    
    try:
        r = redis.from_url(redis_url, decode_responses=True)
        
        # Increment trending (24h window)
        trending_key = _redis_key(kind, slug, "trending")
        pipe = r.pipeline()
        pipe.incr(trending_key)
        pipe.expire(trending_key, TRENDING_WINDOW)
        
        # Increment popular (30d window)
        popular_key = _redis_key(kind, slug, "popular")
        pipe.incr(popular_key)
        pipe.expire(popular_key, POPULAR_WINDOW)
        
        await pipe.execute()
    except Exception:
        pass


@router.get("")
@limiter.limit(get_settings().rate_limit)
async def trending_all(
    limit: int = Query(20, ge=1, le=50),
):
    """Get trending items across all kinds."""
    anime = await _get_top("anime", limit // 3 + 1)
    comic = await _get_top("comic", limit // 3 + 1)
    novel = await _get_top("novel", limit // 3 + 1)
    
    all_items = anime + comic + novel
    all_items.sort(key=lambda x: x["count"], reverse=True)
    
    return {
        "ok": True,
        "source": "trending",
        "data": all_items[:limit],
    }


@router.get("/{kind}")
@limiter.limit(get_settings().rate_limit)
async def trending_kind(
    kind: str,
    limit: int = Query(20, ge=1, le=50),
):
    """Get trending items for a specific kind."""
    if kind not in ("anime", "comic", "novel"):
        return {"ok": False, "source": "trending", "error": f"Invalid kind: {kind}"}
    
    items = await _get_top(kind, limit)
    
    return {
        "ok": True,
        "source": "trending",
        "data": items,
    }


@router.get("/popular/{kind}")
@limiter.limit(get_settings().rate_limit)
async def popular_kind(
    kind: str,
    limit: int = Query(20, ge=1, le=50),
):
    """Get all-time popular items for a specific kind."""
    if kind not in ("anime", "comic", "novel"):
        return {"ok": False, "source": "trending", "error": f"Invalid kind: {kind}"}
    
    items = await _get_top(kind, limit, window="popular")
    
    return {
        "ok": True,
        "source": "trending",
        "data": items,
    }


# Export increment function for other modules to call
__all__ = ["router", "_increment"]
