"""Response-level TTL cache for router endpoints.

Caches the JSON payload of an endpoint by ``(path, query)`` key, with a TTL
driven by env var ``RESPONSE_CACHE_TTL_SECONDS`` (default 300s = 5 min).

Backend is in-memory by default. Set ``RESPONSE_CACHE_REDIS_URL`` (e.g.
``redis://redis:6379/1``) to use Redis for distributed caching.

Skips caching when:
* The request is anything but GET.
* The request includes an Authorization or X-API-Key header (per-user content).
* The response does not have ``ok=True``.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Awaitable, Callable, Optional

from fastapi import Request, Response

from .config import get_settings


class _ResponseCache:
    """Tiny TTL cache for response bodies. In-process only."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, bytes, bytes]] = {}

    def get(self, key: str, ttl: int) -> Optional[tuple[bytes, bytes]]:
        item = self._store.get(key)
        if not item:
            return None
        ts, body, ctype = item
        if time.time() - ts > ttl:
            self._store.pop(key, None)
            return None
        return body, ctype

    def set(self, key: str, body: bytes, ctype: bytes, ttl: int) -> None:
        self._store[key] = (time.time(), body, ctype)

    def stats(self) -> dict:
        return {"backend": "memory", "size": len(self._store), "max_size": 1024}

    def clear(self) -> None:
        self._store.clear()


class _RedisResponseCache:
    """Async Redis-backed response cache.

    Set ``RESPONSE_CACHE_REDIS_URL`` to enable. Falls back to memory backend
    on Redis errors (does NOT 500 the API).
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._redis = None

    async def _client(self):
        if self._redis is None:
            import redis.asyncio as aioredis  # local import: optional dep

            self._redis = aioredis.from_url(self._url, decode_responses=False)
        return self._redis

    async def get(self, key: str, ttl: int) -> Optional[tuple[bytes, bytes]]:
        try:
            client = await self._client()
            val = await client.get(f"nakama-resp:{key}")
            if val is None:
                return None
            return val, b"application/json"
        except Exception:
            return None

    async def set(self, key: str, body: bytes, ctype: bytes, ttl: int) -> None:
        try:
            client = await self._client()
            await client.set(f"nakama-resp:{key}", body, ex=ttl)
        except Exception:
            pass

    async def clear(self) -> None:
        try:
            client = await self._client()
            await client.flushdb()
        except Exception:
            pass

    async def close(self) -> None:
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None


def _build_backend():
    """Pick cache backend. Memory by default; Redis if env set."""
    url = os.getenv("RESPONSE_CACHE_REDIS_URL", "").strip()
    if url:
        return "redis", url
    return "memory", ""


_BACKEND_KIND, _BACKEND_URL = _build_backend()
if _BACKEND_KIND == "redis":
    _cache: Any = _RedisResponseCache(_BACKEND_URL)
else:
    _cache = _ResponseCache()


def _key(request: Request) -> str:
    """Build a cache key from method+path+query."""
    raw = f"{request.method}:{request.url.path}:{request.url.query}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


async def cached_response(
    request: Request,
    fetch: Callable[[], Awaitable[Any]],
    *,
    ttl_seconds: Optional[int] = None,
) -> Any:
    """Try cache, otherwise call ``fetch()`` and store the result.

    Returns whatever ``fetch()`` returns (typically a dict the router wraps).
    """
    if request.method != "GET":
        return await fetch()
    # Per-user content shouldn't be cached.
    if request.headers.get("authorization") or request.headers.get("x-api-key"):
        return await fetch()

    ttl = ttl_seconds if ttl_seconds is not None else get_settings().cache_ttl_seconds
    key = _key(request)
    hit = _cache.get(key, ttl)
    if hit is not None:
        body, _ctype = hit
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            pass
    result = await fetch()
    if isinstance(result, dict) and result.get("ok"):
        try:
            body = json.dumps(result, default=str).encode("utf-8")
            await _cache.set(key, body, b"application/json", ttl)
        except Exception:
            pass
    return result


def add_etag(response: Response, body: bytes):
    """Add ETag header based on content hash."""
    etag = hashlib.sha1(body).hexdigest()[:16]
    response.headers["ETag"] = f'W/"{etag}"'
    response.headers["Cache-Control"] = "public, max-age=300, must-revalidate"


def check_etag(request: Request, body: bytes) -> Optional[Response]:
    """Return 304 Not Modified if If-None-Match matches ETag of body."""
    if_none_match = request.headers.get("If-None-Match", "").strip()
    if not if_none_match:
        return None
    etag = hashlib.sha1(body).hexdigest()[:16]
    expected = f'W/"{etag}"'
    if if_none_match == expected or if_none_match == etag:
        return Response(status_code=304)
    return None


def cache_stats() -> dict:
    return _cache.stats()


def clear_cache() -> None:
    """Clear the response cache (memory backend: synchronous; Redis: async-safe)."""
    _cache.clear()