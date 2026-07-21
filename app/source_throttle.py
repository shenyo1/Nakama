"""Per-source upstream rate limiting.

Some upstreams (MangaDex ~5 rps, Jikan ~3 rps, scrapers behind Cloudflare)
reject bursts. This module enforces a process-wide minimum interval between
calls for selected source labels, plus optional burst capacity.

Usage::

    await throttle_source("mangadex")
    await throttle_source("jikan")

Call sites should pass the same ``source`` label used for metrics.
"""
from __future__ import annotations

import asyncio
import time
from typing import Dict, Optional

# Minimum seconds between calls per source (process-wide).
# Override via env SOURCE_MIN_INTERVAL_<NAME>=0.25 if needed later.
_DEFAULT_INTERVALS: Dict[str, float] = {
    "jikan": 0.40,
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

_LOCKS: Dict[str, asyncio.Lock] = {}
_LAST_CALL: Dict[str, float] = {}
_GLOBAL_LOCK = asyncio.Lock()


def _interval_for(source: str) -> float:
    return float(_DEFAULT_INTERVALS.get(source, 0.0))


async def throttle_source(source: Optional[str]) -> None:
    """Wait until this source is allowed another upstream request."""
    if not source:
        return
    interval = _interval_for(source)
    if interval <= 0:
        return

    async with _GLOBAL_LOCK:
        lock = _LOCKS.get(source)
        if lock is None:
            lock = asyncio.Lock()
            _LOCKS[source] = lock

    async with lock:
        now = time.monotonic()
        last = _LAST_CALL.get(source, 0.0)
        wait = interval - (now - last)
        if wait > 0:
            await asyncio.sleep(wait)
        _LAST_CALL[source] = time.monotonic()


def source_intervals() -> Dict[str, float]:
    """Expose configured intervals for health/debug endpoints."""
    return dict(_DEFAULT_INTERVALS)
