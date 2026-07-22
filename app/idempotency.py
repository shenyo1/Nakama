"""
Idempotency-Key middleware (Stripe pattern).

For POST and PATCH requests, clients can send an `Idempotency-Key` header.
The first request with a given key is processed normally and its response is
cached. Subsequent requests with the same key return the cached response
without re-executing the handler.

This prevents duplicate operations when clients (especially AI agents) retry
requests due to network timeouts.

Cache TTL: 24 hours (configurable via IDEMPOTENCY_TTL_SECONDS).
Storage: Redis with in-memory fallback.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from .config import get_settings

_IDEMPOTENCY_TTL = 86400  # 24 hours
_CACHE: dict[str, tuple[float, bytes, int, str]] = {}  # key → (expires_at, body, status, content_type)
_LOCK = asyncio.Lock()


def _cache_key(request: Request) -> str:
    """Derive a stable cache key from Idempotency-Key + method + path."""
    key = request.headers.get("Idempotency-Key", "").strip()
    if not key:
        return ""
    raw = f"{key}|{request.method}|{request.url.path}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def _redis_get(key: str) -> Optional[dict]:
    """Get cached response from Redis."""
    try:
        s = get_settings()
        if not s.redis_url:
            return None
        import redis.asyncio as aioredis
        client = aioredis.from_url(s.redis_url, decode_responses=True)
        try:
            raw = await client.get(f"idem:{key}")
            if raw:
                return json.loads(raw)
        finally:
            await client.aclose()
    except Exception:
        pass
    return None


async def _redis_set(key: str, data: dict, ttl: int = _IDEMPOTENCY_TTL):
    """Cache response in Redis."""
    try:
        s = get_settings()
        if not s.redis_url:
            return
        import redis.asyncio as aioredis
        client = aioredis.from_url(s.redis_url)
        try:
            await client.setex(f"idem:{key}", ttl, json.dumps(data))
        finally:
            await client.aclose()
    except Exception:
        pass


async def _local_get(key: str) -> Optional[tuple[int, bytes, str]]:
    """Get cached response from in-memory store."""
    if key not in _CACHE:
        return None
    expires, body, status, ct = _CACHE[key]
    if time.time() > expires:
        del _CACHE[key]
        return None
    return status, body, ct


def _local_set(key: str, status: int, body: bytes, content_type: str):
    """Cache response in in-memory store."""
    _CACHE[key] = (time.time() + _IDEMPOTENCY_TTL, body, status, content_type)
    # Prevent unbounded growth: keep max 1000 entries
    if len(_CACHE) > 1000:
        oldest = min(_CACHE, key=lambda k: _CACHE[k][0])
        del _CACHE[oldest]


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware that handles Idempotency-Key for POST and PATCH requests."""

    async def dispatch(self, request: Request, call_next):
        # Only apply to mutation methods
        if request.method not in ("POST", "PATCH"):
            return await call_next(request)

        key = request.headers.get("Idempotency-Key", "").strip()
        if not key:
            return await call_next(request)

        cache_key = _cache_key(request)

        # Check cache
        async with _LOCK:
            cached = await _local_get(cache_key)

        if cached is not None:
            status, body, ct = cached
            return Response(content=body, status_code=status, media_type=ct,
                          headers={"Idempotency-Replayed": "true"})

        # Check Redis
        redis_data = await _redis_get(cache_key)
        if redis_data:
            return Response(
                content=redis_data["body"].encode() if isinstance(redis_data["body"], str) else redis_data["body"],
                status_code=redis_data["status"],
                media_type=redis_data.get("content_type", "application/json"),
                headers={"Idempotency-Replayed": "true"},
            )

        # Process normally
        response = await call_next(request)

        # Cache the response
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        ct = response.headers.get("content-type", "application/json")

        async with _LOCK:
            _local_set(cache_key, response.status_code, body, ct)

        # Also cache in Redis (fire-and-forget)
        asyncio.create_task(_redis_set(cache_key, {
            "body": body.decode() if isinstance(body, bytes) else body,
            "status": response.status_code,
            "content_type": ct,
        }))

        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=ct,
        )
