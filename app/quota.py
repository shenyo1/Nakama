"""Per-user daily quota (Redis with in-memory fallback) + tiered burst limits."""
from __future__ import annotations

import asyncio
import time
from typing import Dict, Optional, Tuple

from .config import get_settings

# plan -> daily request budget for /anime|/comic|/novel|/search|/history
PLAN_QUOTAS: Dict[str, int] = {
    "free": 1000,
    "pro": 10000,
    "unlimited": 0,  # 0 means unlimited
}

# Tiered burst limits: (requests, window_seconds) per plan
# Allows short bursts while keeping the daily cap
BURST_LIMITS: Dict[str, Tuple[int, int]] = {
    "free": (30, 60),        # 30 req per 60s
    "pro": (200, 60),        # 200 req per 60s
    "unlimited": (1000, 60), # 1000 req per 60s
}

_LOCAL_COUNTS: Dict[str, Tuple[str, int]] = {}  # key -> (day, count)
_BURST_WINDOW: Dict[str, list] = {}  # key -> [timestamps]
_REDIS = None
_REDIS_FAILED = False
_LOCK = asyncio.Lock()


def quota_for_plan(plan: str) -> int:
    return int(PLAN_QUOTAS.get(plan or "free", PLAN_QUOTAS["free"]))


def burst_limit_for_plan(plan: str) -> Tuple[int, int]:
    return BURST_LIMITS.get(plan or "free", BURST_LIMITS["free"])


async def check_burst(subject: str, plan: str = "free") -> dict:
    """Check if subject is within burst limits.

    Returns {allowed, burst_limit, burst_window_s, burst_used}.
    """
    limit, window = burst_limit_for_plan(plan)
    now = time.monotonic()
    key = f"burst:{subject}"

    # Redis path
    r = await _redis()
    if r is not None:
        try:
            redis_key = f"nakama:{key}"
            count = await r.zcard(redis_key)
            if count >= limit:
                # Check if oldest entry is still within window
                oldest = await r.zrange(redis_key, 0, 0, withscores=True)
                if oldest and (now - oldest[0][1]) < window:
                    return {
                        "allowed": False,
                        "burst_limit": limit,
                        "burst_window_s": window,
                        "burst_used": int(count),
                    }
                # Clean expired entries
                await r.zremrangebyscore(redis_key, 0, now - window)
            await r.zadd(redis_key, {str(now): now})
            await r.expire(redis_key, window + 10)
            return {
                "allowed": True,
                "burst_limit": limit,
                "burst_window_s": window,
                "burst_used": int(count) + 1 if count < limit else 1,
            }
        except Exception:
            pass

    # Memory fallback
    timestamps = _BURST_WINDOW.get(key, [])
    timestamps = [t for t in timestamps if now - t < window]
    if len(timestamps) >= limit:
        _BURST_WINDOW[key] = timestamps
        return {
            "allowed": False,
            "burst_limit": limit,
            "burst_window_s": window,
            "burst_used": len(timestamps),
        }
    timestamps.append(now)
    _BURST_WINDOW[key] = timestamps
    return {
        "allowed": True,
        "burst_limit": limit,
        "burst_window_s": window,
        "burst_used": len(timestamps),
    }


async def _redis():
    global _REDIS, _REDIS_FAILED
    if _REDIS_FAILED:
        return None
    if _REDIS is not None:
        return _REDIS
    async with _LOCK:
        if _REDIS is not None:
            return _REDIS
        try:
            url = get_settings().redis_url
            if not url:
                _REDIS_FAILED = True
                return None
            import redis.asyncio as aioredis

            client = aioredis.from_url(url, decode_responses=True)
            await client.ping()
            _REDIS = client
            return _REDIS
        except Exception:
            _REDIS_FAILED = True
            return None


def _day_key() -> str:
    return time.strftime("%Y%m%d", time.gmtime())


async def check_and_increment(subject: str, plan: str = "free") -> dict:
    """Increment daily counter for subject (user id or 'apikey'/'anon').

    Returns {allowed, used, limit, plan, remaining}.
    """
    limit = quota_for_plan(plan)
    if limit == 0:
        return {"allowed": True, "used": 0, "limit": 0, "plan": plan, "remaining": None}

    day = _day_key()
    key = f"nakama:quota:{day}:{subject}"
    r = await _redis()
    if r is not None:
        try:
            used = await r.incr(key)
            if used == 1:
                await r.expire(key, 60 * 60 * 36)  # expire after ~1.5 days
            allowed = used <= limit
            return {
                "allowed": allowed,
                "used": int(used),
                "limit": limit,
                "plan": plan,
                "remaining": max(0, limit - int(used)),
            }
        except Exception:
            pass

    # memory fallback
    prev_day, count = _LOCAL_COUNTS.get(key, (day, 0))
    if prev_day != day:
        count = 0
    count += 1
    _LOCAL_COUNTS[key] = (day, count)
    return {
        "allowed": count <= limit,
        "used": count,
        "limit": limit,
        "plan": plan,
        "remaining": max(0, limit - count),
    }


async def peek(subject: str, plan: str = "free") -> dict:
    limit = quota_for_plan(plan)
    if limit == 0:
        return {"used": 0, "limit": 0, "plan": plan, "remaining": None}
    day = _day_key()
    key = f"nakama:quota:{day}:{subject}"
    r = await _redis()
    used = 0
    if r is not None:
        try:
            val = await r.get(key)
            used = int(val or 0)
            return {
                "used": used,
                "limit": limit,
                "plan": plan,
                "remaining": max(0, limit - used),
            }
        except Exception:
            pass
    prev_day, count = _LOCAL_COUNTS.get(key, (day, 0))
    used = count if prev_day == day else 0
    return {"used": used, "limit": limit, "plan": plan, "remaining": max(0, limit - used)}
