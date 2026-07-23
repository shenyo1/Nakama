"""Shared Redis client singleton for Nakama.

Centralizes connection so security, idempotency, response cache, quota, and
revocation lists all share the same pool. Falls back to None if Redis is
unreachable — callers must handle the None case (e.g. log and skip).
"""

from __future__ import annotations

import os
from typing import Optional

_client = None
_client_failed = False


def get_redis_url() -> str:
    return os.getenv("REDIS_URL") or os.getenv("REDIS_HOST", "redis://localhost:6379")


def get_redis():
    """Return a cached async Redis client, or None if unavailable."""
    global _client, _client_failed
    if _client is not None:
        return _client
    if _client_failed:
        return None
    try:
        import redis.asyncio as aioredis

        _client = aioredis.from_url(get_redis_url(), decode_responses=True)
        return _client
    except Exception:
        _client_failed = True
        return None


async def close_redis() -> None:
    global _client
    if _client is not None:
        try:
            await _client.close()
        except Exception:
            pass
        _client = None