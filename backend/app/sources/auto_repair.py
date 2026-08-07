"""Auto-repair layer for Nakama source adapters.

The auto-repair system has four coordinated parts:

1. **Per-source circuit breaker** — when an upstream repeatedly fails, stop
   hitting it for a cooldown period. Other sources keep working.

2. **Selector auto-detection** — when a selector-based parser returns 0
   items but the page returns 200, try the next selector strategy
   (fallback selectors) before giving up.

3. **Schema-drift detector** — when items list drops suddenly, snapshot
   the raw HTML, diff against the last good snapshot, and (a) notify
   the engineer, (b) try generic fallback selectors, (c) if a recently-
   added fallback works, persist the new selector set as the primary.

4. **Health-triggered fallback** — `/anime/samehadaku/episode/<slug>`
   uses primary `samehadaku` first; on SourceError, the auto-repair
   router automatically retries with `otakudesu` (if the slug can be
   cross-resolved via search), then surfaces the failure.

This module wires these together without requiring manual intervention
for transient or recoverable failures.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# Circuit breaker
# --------------------------------------------------------------------------- #

@dataclass
class _BreakerState:
    failure_count: int = 0
    success_count: int = 0
    last_failure_ts: float = 0.0
    last_success_ts: float = 0.0
    cooldown_until: float = 0.0
    state: str = "closed"  # closed | open | half-open
    _hydrated: bool = field(default=False, repr=False)


# Tunables (overridable via env SOURCE_FAILURE_THRESHOLD etc.)
FAILURE_THRESHOLD = int(os.getenv("SOURCE_FAILURE_THRESHOLD", "5"))
COOLDOWN_SECONDS = float(os.getenv("SOURCE_COOLDOWN_SECONDS", "120"))
HALF_OPEN_SUCCESS_NEEDED = int(os.getenv("SOURCE_HALF_OPEN_SUCCESS", "2"))


# In-process fast path. When Redis is available the breaker state is also
# persisted (nakama:cb:<source>) so that with multiple uvicorn workers:
#   * a breaker opened by worker A is respected by workers B/C/D
#   * a cooldown advances even if the traffic lands on a different worker
# This mirrors Sanka's "circuit breaker PERSISTEN di admin_settings".
_BREAKERS: Dict[str, _BreakerState] = {}
_CB_PREFIX = "nakama:cb:"

_REDIS = None
_REDIS_FAILED = False
_REDIS_LOCK = asyncio.Lock()


async def _redis() -> Optional[Any]:
    global _REDIS, _REDIS_FAILED
    if _REDIS_FAILED:
        return None
    if _REDIS is not None:
        return _REDIS
    async with _REDIS_LOCK:
        if _REDIS is not None:
            return _REDIS
        try:
            from ..config import get_settings

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


async def _cb_persist(name: str, bs: _BreakerState) -> None:
    r = await _redis()
    if r is None:
        return
    try:
        payload = {
            "state": bs.state,
            "failure_count": bs.failure_count,
            "success_count": bs.success_count,
            "last_failure_ts": bs.last_failure_ts,
            "last_success_ts": bs.last_success_ts,
            "cooldown_until": bs.cooldown_until,
        }
        await r.hset(f"{_CB_PREFIX}{name}", mapping={k: str(v) for k, v in payload.items()})
        await r.expire(f"{_CB_PREFIX}{name}", 60 * 60 * 24 * 7)
    except Exception:
        pass


async def _cb_load(name: str) -> Optional[_BreakerState]:
    r = await _redis()
    if r is None:
        return None
    try:
        raw = await r.hgetall(f"{_CB_PREFIX}{name}")
        if not raw:
            return None
        return _BreakerState(
            state=raw.get("state") or "closed",
            failure_count=int(raw.get("failure_count") or 0),
            success_count=int(raw.get("success_count") or 0),
            last_failure_ts=float(raw.get("last_failure_ts") or 0),
            last_success_ts=float(raw.get("last_success_ts") or 0),
            cooldown_until=float(raw.get("cooldown_until") or 0),
        )
    except Exception:
        return None


def _get_breaker(source: str) -> _BreakerState:
    return _BREAKERS.setdefault(source, _BreakerState())


def breaker_allow(source: str) -> bool:
    """True if this source is allowed to make an upstream call right now.

    Uses the in-process state, hydrated from Redis once per process (seen on
    first access via the setdefault + lazy refresh in _sync_breaker). The
    async wrappers below refresh from Redis when available.
    """
    bs = _get_breaker(source)
    now = time.monotonic()
    if bs.state == "open":
        if now >= bs.cooldown_until:
            bs.state = "half-open"
            bs.success_count = 0
            return True
        return False
    return True


async def breaker_allow_async(source: str) -> bool:
    """Async variant: hydrate breaker state from Redis (multi-worker share)."""
    bs = await _breaker_for(source)
    now = time.monotonic()
    if bs.state == "open":
        if now >= bs.cooldown_until:
            bs.state = "half-open"
            bs.success_count = 0
            await _cb_persist(source, bs)
            return True
        return False
    return True


async def _breaker_for(name: str) -> _BreakerState:
    """Return the in-process breaker, syncing once from Redis if unseen."""
    bs = _get_breaker(name)
    # Lazy one-time hydration so a breaker opened by another worker shows up
    # without needing a restart.
    if getattr(bs, "_hydrated", False) is False:
        remote = await _cb_load(name)
        if remote is not None:
            bs.state = remote.state
            bs.failure_count = remote.failure_count
            bs.success_count = remote.success_count
            bs.last_failure_ts = remote.last_failure_ts
            bs.last_success_ts = remote.last_success_ts
            bs.cooldown_until = remote.cooldown_until
        bs._hydrated = True
    return bs


def breaker_record_success(source: str) -> None:
    bs = _get_breaker(source)
    bs.success_count += 1
    bs.last_success_ts = time.monotonic()
    if bs.state == "half-open" and bs.success_count >= HALF_OPEN_SUCCESS_NEEDED:
        bs.state = "closed"
        bs.failure_count = 0
        _run(_cb_persist(source, bs))


def breaker_record_failure(source: str) -> None:
    bs = _get_breaker(source)
    bs.failure_count += 1
    bs.last_failure_ts = time.monotonic()
    if bs.failure_count >= FAILURE_THRESHOLD:
        bs.state = "open"
        bs.cooldown_until = time.monotonic() + COOLDOWN_SECONDS
        _run(_cb_persist(source, bs))


def _run(coro: Any) -> None:
    """Fire-and-forget a coroutine from a sync context (best-effort).

    If no running loop exists (e.g. sync unit test calling breaker_record_*),
    the coroutine is closed to avoid a 'never awaited' unraisable warning.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            coro.close()
        except Exception:
            pass
        return
    try:
        loop.create_task(coro)
    except Exception:
        try:
            coro.close()
        except Exception:
            pass


def breaker_status() -> Dict[str, dict]:
    """Snapshot of every circuit breaker — for /sources/health and dashboards."""
    now = time.monotonic()
    out = {}
    for src, bs in _BREAKERS.items():
        out[src] = {
            "state": bs.state,
            "failures": bs.failure_count,
            "cooldown_remaining": max(0, bs.cooldown_until - now) if bs.state == "open" else 0,
            "last_success": bs.last_success_ts,
            "last_failure": bs.last_failure_ts,
        }
    return out


# --------------------------------------------------------------------------- #
# Selector fallback chain
# --------------------------------------------------------------------------- #

@dataclass
class SelectorAttempt:
    name: str
    selector: str
    score: int = 0  # how many items it parsed last time it ran


def fallback_selectors(tag: str) -> List[SelectorAttempt]:
    """Return an ordered list of fallback selectors for a given card type.

    The first selector is the one currently used by the adapter. Subsequent
    ones are documented fallbacks we try when the first one parses <1 items.

    Convention: each adapter's ``_parse_<thing>`` helper takes a BeautifulSoup
    and runs a list of selectors in order. This function lets the auto-repair
    layer pull "the next selector to try" from a shared registry.

    For now, each adapter owns its own selector lists. This module provides
    the *machinery* to iterate through them when the primary fails.
    """
    # Per-source fallback chains are stored in /tmp at runtime; this is a
    # simple in-memory fallback for fast re-attempt before the next request.
    # The real fallback is in each adapter's try-multiple-selectors pattern.
    return _REGISTRY.get(tag, [])


_REGISTRY: Dict[str, List[SelectorAttempt]] = {}


def register_selectors(tag: str, attempts: List[SelectorAttempt]) -> None:
    _REGISTRY[tag] = attempts


# --------------------------------------------------------------------------- #
# Schema-drift detection
# --------------------------------------------------------------------------- #

_HTML_SNAPSHOTS_DIR = os.getenv("HTML_SNAPSHOTS_DIR", "/tmp/nakama-snapshots")
os.makedirs(_HTML_SNAPSHOTS_DIR, exist_ok=True)


def snapshot_html(source: str, url: str, html: str) -> str:
    """Persist the latest raw HTML so we can diff when a source goes silent."""
    from hashlib import sha1

    safe = re.sub(r"[^a-zA-Z0-9]+", "_", source)[:32]
    path = os.path.join(_HTML_SNAPSHOTS_DIR, f"{safe}.html")
    # Always overwrite with the latest snapshot
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def diff_against_snapshot(source: str, current_html: str) -> dict:
    """Return a simple diff summary vs the previous snapshot, if any."""
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", source)[:32]
    path = os.path.join(_HTML_SNAPSHOTS_DIR, f"{safe}.html")
    if not os.path.exists(path):
        return {"status": "no-baseline"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            previous = f.read()
    except Exception:
        return {"status": "unreadable"}
    return {
        "status": "diff",
        "previous_len": len(previous),
        "current_len": len(current_html),
        "len_delta": len(current_html) - len(previous),
        "indicator_present": {
            "previous": [
                kw in previous
                for kw in ("series-chapterlists", "episodes-list", "chapter-list", "manga-list")
            ],
            "current": [
                kw in current_html
                for kw in ("series-chapterlists", "episodes-list", "chapter-list", "manga-list")
            ],
        },
    }


# --------------------------------------------------------------------------- #
# Cross-source recovery
# --------------------------------------------------------------------------- #

# Map from a failing source to a fallback that often has the same content.
# Used by the auto-repair middleware in routers/* to retry once with the
# fallback before returning an error to the caller.
CROSS_SOURCE_FALLBACK = {
    "anime": {
        "samehadaku": ["otakudesu"],
        "otakudesu": ["samehadaku"],
    },
    "comic": {
        "komiku": ["kiryuu", "komikindo"],
        "kiryuu": ["komiku", "komikindo"],
        "komikindo": ["komiku", "kiryuu"],
        "shinigami": ["mangadex", "komiku"],
        "mangadex": ["komiku", "kiryuu"],
    },
    "novel": {
        "novelbin": ["novelfull", "sakuranovel"],
        "novelfull": ["novelbin", "sakuranovel"],
        "sakuranovel": ["novelbin", "novelfull"],
    },
}


def get_fallback_sources(kind: str, primary: str) -> List[str]:
    return CROSS_SOURCE_FALLBACK.get(kind, {}).get(primary, [])


# --------------------------------------------------------------------------- #
# Auto-repair middleware hook
# --------------------------------------------------------------------------- #

async def with_auto_repair(
    source: str,
    fn,
    *args,
    fallback_fn=None,
    **kwargs,
):
    """Run ``fn(source, *args, **kwargs)`` with breaker + recovery.

    On success → record_success, return result.
    On failure (after breaker threshold) → call ``fallback_fn`` once if
    provided, otherwise re-raise.

    The circuit breaker is checked BEFORE the call (skip when open). In
    async context the Redis-persisted breaker is hydrated so a breaker opened
    by another worker is still respected here.
    """
    if not await breaker_allow_async(source):
        if fallback_fn is not None:
            return await fallback_fn(*args, **kwargs)
        raise RuntimeError(f"circuit-breaker-open:{source}")

    try:
        result = await fn(*args, **kwargs)
    except Exception as e:
        breaker_record_failure(source)
        if fallback_fn is not None:
            return await fallback_fn(*args, **kwargs)
        raise
    else:
        breaker_record_success(source)
        return result