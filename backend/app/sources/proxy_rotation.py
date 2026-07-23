"""Rotating proxy support for high-block sources.

Use case: providers like samehadaku / otakudesu / novelfull sometimes
rate-limit or block our outbound IP. FlareSolverr solves CF challenges,
but doesn't help with pure IP throttling. This module adds a layer of
outbound proxies so each request rotates through a different IP.

Configuration (env vars, optional):
- ``PROXY_URL``              single proxy URL, applied to all upstreams
                              Example: ``http://user:pass@proxy.example.com:8080``
- ``PROXY_URL_<SOURCE>``     per-source override, e.g. ``PROXY_URL_KOMIKCAST``
- ``PROXY_POOL``             comma-separated URLs for rotation, e.g.
                              ``http://p1:8080,http://p2:8080``
- ``PROXY_POOL_<SOURCE>``    per-source pool, e.g. ``PROXY_POOL_SAKURANOVEL``
- ``PROXY_DISABLE_FOR``      comma-separated source names to skip proxying,
                              e.g. ``anilist,jikan,mangadex``

When the module can't find a proxy, the call falls through to direct
(no-op). Failures with a proxy are retried with the next one in the pool
(up to ``PROXY_MAX_RETRIES`` times, default 2).

Implementation notes:
- Each fetch_soup / fetch_json call passes ``source=`` which this module
  uses to pick the right proxy config.
- Proxy state is process-local (one rotation counter per source).
"""
from __future__ import annotations

import itertools
import os
import threading
from typing import Dict, Iterator, List, Optional


_PROXY_LOCK = threading.Lock()
_ROTATION_INDEX: Dict[str, Iterator[int]] = {}


def _get_pool(source: str) -> Optional[List[str]]:
    """Resolve the proxy pool for ``source`` (or None)."""
    pool_env = os.getenv(f"PROXY_POOL_{source.upper()}")
    if pool_env:
        return [p.strip() for p in pool_env.split(",") if p.strip()]
    if pool_env is None:
        # Fall back to global PROXY_POOL
        pool_env = os.getenv("PROXY_POOL")
    if pool_env:
        return [p.strip() for p in pool_env.split(",") if p.strip()]
    # Single URL fallback
    single = os.getenv(f"PROXY_URL_{source.upper()}") or os.getenv("PROXY_URL")
    return [single] if single else None


def is_disabled_for(source: str) -> bool:
    """True if proxying is disabled for this source."""
    disabled = os.getenv("PROXY_DISABLE_FOR", "")
    return source.lower() in {s.strip().lower() for s in disabled.split(",") if s.strip()}


def next_proxy(source: str) -> Optional[str]:
    """Pick the next proxy URL for ``source`` (round-robin).

    Returns None if no proxy configured or proxying is disabled for this source.
    """
    if is_disabled_for(source):
        return None
    pool = _get_pool(source)
    if not pool:
        return None
    with _PROXY_LOCK:
        if source not in _ROTATION_INDEX or _ROTATION_INDEX[source] is None:
            _ROTATION_INDEX[source] = itertools.cycle(range(len(pool)))
        idx = next(_ROTATION_INDEX[source])
    return pool[idx]


def max_retries() -> int:
    return int(os.getenv("PROXY_MAX_RETRIES", "2"))


def status() -> Dict[str, dict]:
    """Snapshot of which sources have proxies configured."""
    sources = [
        "otakudesu", "samehadaku", "anilist", "jikan",
        "komiku", "kiryuu", "komikcast", "komikindo", "mangadex", "shinigami",
        "sakuranovel", "novelbin", "novelfull",
    ]
    out = {}
    for s in sources:
        pool = _get_pool(s)
        out[s] = {
            "proxy_enabled": pool is not None and not is_disabled_for(s),
            "pool_size": len(pool) if pool else 0,
            "disabled_for": is_disabled_for(s),
        }
    return out