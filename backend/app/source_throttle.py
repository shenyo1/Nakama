"""Per-source upstream rate limiting with adaptive auto-tuning.

Some upstreams (MangaDex ~5 rps, Jikan ~3 rps, scrapers behind Cloudflare)
reject bursts. This module enforces a process-wide minimum interval between
calls for selected source labels, plus optional burst capacity.

Adaptive behavior (learned from Sanka's ``providerRuntime.auto_tune``):

* Each source has a minimum and maximum interval.
* On a rate-limit / failure streak the source's effective interval grows
  (slower) by 25% — backs off to respect the upstream.
* After a sustained run of successes the interval shrinks (faster) by 15%
  back toward the source's base, capped at the configured minimum.

Usage::

    await throttle_source("mangadex")
    await throttle_source("jikan")

Call sites should pass the same ``source`` label used for metrics.
"""
from __future__ import annotations

import asyncio
import time
from typing import Dict, Optional

# Base minimum seconds between calls per source. Adaptive tuning lets the
# effective interval move up (rate-limit) and down (success) within
# [min, min*MAX_BACKOFF]. Override via env SOURCE_MIN_INTERVAL_<NAME>=0.25.
_DEFAULT_MIN_INTERVAL: Dict[str, float] = {
    "jikan": 0.75,  # Jikan v4 is rate-sensitive (~3 rps but bursty); 0.75s ≈ 1.3 rps
    "mangadex": 0.25,
    "komiku": 0.15,
    "kiryuu": 0.15,
    "shinigami": 0.20,
    "otakudesu": 0.20,
    "kura": 0.20,
    "sakuranovel": 0.50,  # FlareSolverr is expensive
    "komikcast": 0.15,
    "anilist": 0.20,
}

# How far the effective interval may back off above its base before capping.
MAX_BACKOFF = float(__import__("os").getenv("SOURCE_MAX_BACKOFF", "4.0"))
# Out of every HOW_MANY_SUCCESS a backoff-of-15% is granted (Sanka: after 200).
TUNE_WINDOW = int(__import__("os").getenv("SOURCE_TUNE_WINDOW", "200"))
# Growing interval step on a failure/rate-limit (Sanka: shrink 25% slower).
BACKOFF_STEP = float(__import__("os").getenv("SOURCE_BACKOFF_STEP", "1.25"))
# Shrinking interval step on a sustained success run (Sanka: grow 15% faster).
RECOVER_STEP = float(__import__("os").getenv("SOURCE_RECOVER_STEP", "0.85"))


class _Throttle:
    __slots__ = ("min_interval", "interval", "lock", "last_call", "streak", "since_window")


def _make_throttle(source: str) -> _Throttle:
    base = float(_DEFAULT_MIN_INTERVAL.get(source, 0.0))
    t = _Throttle()
    t.min_interval = base
    t.interval = base
    t.lock = asyncio.Lock()
    t.last_call = 0.0
    t.streak = 0
    t.since_window = 0
    return t


_THROTTLES: Dict[str, _Throttle] = {}
_GLOBAL_LOCK = asyncio.Lock()


def _get(source: str) -> Optional[_Throttle]:
    global _THROTTLES
    t = _THROTTLES.get(source)
    if t is None:
        base = float(_DEFAULT_MIN_INTERVAL.get(source, 0.0))
        if base <= 0:
            return None  # not throttled
        t = _make_throttle(source)
        _THROTTLES[source] = t
    return t


def _interval_for(source: str) -> float:
    t = _get(source)
    return t.interval if t is not None else 0.0


async def throttle_source(source: Optional[str]) -> None:
    """Wait until this source is allowed another upstream request.

    Applies adaptive backoff/recovery based on recent outcome history, then
    sleeps for at least ``interval - time_since_last_call``.
    """
    if not source:
        return
    t = _get(source)
    if t is None:
        return

    async with t.lock:
        now = time.monotonic()
        wait = t.interval - (now - t.last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        t.last_call = time.monotonic()


def record_source_rate_limit(source: Optional[str]) -> None:
    """Call when the upstream returned 429/rate-limited (or a burst error).

    Backs the source off: interval *= BACKOFF_STEP (slower), capped at
    ``min_interval * MAX_BACKOFF``, and resets the success window.
    """
    if not source:
        return
    t = _get(source)
    if t is None:
        return
    t.interval = min(t.min_interval * MAX_BACKOFF, t.interval * BACKOFF_STEP if t.interval > 0 else t.min_interval)
    t.streak = 0
    t.since_window = 0


def record_source_success(source: Optional[str]) -> None:
    """Call when an upstream call succeeded.

    After a sustained run of successes (TUNE_WINDOW) the interval shrinks by
    RECOVER_STEP (faster) back toward the source's base minimum.
    """
    if not source:
        return
    t = _get(source)
    if t is None:
        return
    t.streak += 1
    if t.since_window >= TUNE_WINDOW:
        t.interval = max(t.min_interval, t.interval * RECOVER_STEP)
        t.since_window = 0
    else:
        t.since_window += 1


def source_intervals() -> Dict[str, float]:
    """Expose current effective intervals for health/debug endpoints."""
    out: Dict[str, float] = {}
    for name, interval in _DEFAULT_MIN_INTERVAL.items():
        t = _get(name)
        out[name] = round(t.interval, 4) if t is not None else interval
    return out


def source_throttle_detail() -> Dict[str, dict]:
    """Human/debug-friendly view of every throttle's live tuning state."""
    out: Dict[str, dict] = {}
    for name in _DEFAULT_MIN_INTERVAL:
        t = _get(name)
        if t is None:
            continue
        out[name] = {
            "base_seconds": t.min_interval,
            "current_seconds": round(t.interval, 4),
            "streak": t.streak,
            "since_window": t.since_window,
        }
    return out
