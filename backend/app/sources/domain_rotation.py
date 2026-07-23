"""Domain auto-rotation for sources with cycling base URLs.

Some Indonesian providers (kiryuu, sakuranovel, novelfull) cycle through
multiple base domains. When the configured domain goes down, this module:

1. Reads the source's ``meta.alt_domains`` list.
2. Resolves each alternative domain via DNS (cached).
3. Tries an HTTP HEAD against the live URL — picks the first 2xx/3xx.
4. Returns the working base URL.

The selected domain is cached in Redis/memory for ``CACHE_TTL_SECONDS``
(default 6h) so we don't hammer DNS on every request.

Usage:
    from .domain_rotation import resolve_base_url

    base = await resolve_base_url("kiryuu", "https://kiryuu.id")
    if base:
        # Use `base` instead of the hard-coded URL.
        ...
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx


CACHE_TTL_SECONDS = int(os.getenv("DOMAIN_CACHE_TTL", str(6 * 3600)))
DNS_TIMEOUT = float(os.getenv("DOMAIN_RESOLVE_TIMEOUT", "2.0"))
HTTP_TIMEOUT = float(os.getenv("DOMAIN_HTTP_TIMEOUT", "5.0"))

# In-memory fallback cache: source_name -> (selected_url, expires_at)
_CACHE: Dict[str, Tuple[str, float]] = {}
_CACHE_LOCK = asyncio.Lock()


async def _resolve_dns(host: str) -> bool:
    """Return True if the host resolves via the system resolver."""
    import socket

    try:
        loop = asyncio.get_event_loop()
        await asyncio.wait_for(
            loop.getaddrinfo(host, None), timeout=DNS_TIMEOUT
        )
        return True
    except Exception:
        return False


async def _http_alive(url: str) -> bool:
    """Return True if URL returns 2xx/3xx (cheap HEAD)."""
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as c:
            r = await c.head(url)
            return r.status_code < 400
    except Exception:
        return False


async def resolve_base_url(
    source_name: str,
    primary: str,
    alt_domains: Optional[List[str]] = None,
) -> Optional[str]:
    """Pick a working base URL for ``source_name``.

    Order of preference:
    1. Cached URL (if not expired)
    2. The primary URL (if DNS + HEAD succeed)
    3. Each alt_domains entry (in order), DNS + HEAD check

    Returns the chosen URL or None if nothing works.
    """
    if not primary:
        return None

    async with _CACHE_LOCK:
        cached = _CACHE.get(source_name)
        if cached and cached[1] > time.monotonic():
            return cached[0]

    candidates: List[str] = [primary]
    if alt_domains:
        for d in alt_domains:
            url = primary if "://" in d else f"{urlparse(primary).scheme}://{d}"
            if url not in candidates:
                candidates.append(url)

    for url in candidates:
        host = urlparse(url).hostname or ""
        if not host:
            continue
        if not await _resolve_dns(host):
            continue
        if not await _http_alive(url):
            continue
        # Pick this URL and cache
        async with _CACHE_LOCK:
            _CACHE[source_name] = (url, time.monotonic() + CACHE_TTL_SECONDS)
        return url

    return None


def cache_clear(source_name: Optional[str] = None) -> None:
    """Drop the rotation cache (testing / forced re-resolve)."""
    if source_name is None:
        _CACHE.clear()
    else:
        _CACHE.pop(source_name, None)


def cache_status() -> Dict[str, dict]:
    """Snapshot of cached URLs for /sources/health."""
    now = time.monotonic()
    out = {}
    for name, (url, expires) in _CACHE.items():
        out[name] = {
            "url": url,
            "expires_in_seconds": max(0, int(expires - now)),
        }
    return out