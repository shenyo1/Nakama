"""Response-level TTL cache for router endpoints.

Caches the JSON payload of an endpoint by ``(path, query)`` key, with a TTL
driven by env var ``RESPONSE_CACHE_TTL_SECONDS`` (default 300s = 5 min).

Uses the same in-memory / Redis backend as ``app.http`` so it benefits from
distributed caching when REDIS_URL is set.

Skips caching when:
* The request is anything but GET.
* The request includes an Authorization header (per-user content).
* The response status is not 200.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Awaitable, Callable, Optional

from fastapi import Request, Response

from .config import get_settings


class _ResponseCache:
    """Tiny TTL cache for response bodies. In-memory only by default; the
    Redis backend is reused from app.http via :func:`_get_store` if available.
    """

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

    def set(self, key: str, body: bytes, ctype: bytes) -> None:
        self._store[key] = (time.time(), body, ctype)

    def stats(self) -> dict:
        return {"size": len(self._store), "max_size": 1024}

    def clear(self) -> None:
        self._store.clear()


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
        body, ctype = hit
        # Re-hydrate through JSON so endpoints keep returning ApiResponse.
        return json.loads(body.decode("utf-8"))
    result = await fetch()
    if isinstance(result, dict) and result.get("ok"):
        try:
            body = json.dumps(result, default=str).encode("utf-8")
            _cache.set(key, body, b"application/json")
        except Exception:
            pass
    return result


def cache_stats() -> dict:
    return _cache.stats()


def clear_cache() -> None:
    """Clear the response cache. Useful for tests and admin endpoints."""
    _cache.clear()
