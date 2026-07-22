"""Shared HTTP + cache layer.

- Honours OFFLINE_MODE (serves fixture files instead of the network).
- Short TTL cache to avoid hammering upstream sites.
- Cache backend is pluggable: in-memory dict by default; Redis (via
  ``redis.asyncio``) when ``REDIS_URL`` is set. The async interface is the
  same for both, so call sites do not care which backend is active.
- Emits Prometheus metrics: ``source_requests_total`` for upstream fetches and
  ``cache_hits_total`` / ``cache_misses_total`` for cache lookups. The optional
  ``_metrics_source`` parameter on internal helpers carries the source name
  (e.g. ``"otakudesu"``) so the counter labels stay useful.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .config import get_settings
from .metrics import cache_hits_total, cache_misses_total, source_requests_total
from .source_throttle import throttle_source


def _record(source: Optional[str], *, success: bool, started: float, error: Optional[str] = None) -> None:
    if not source:
        return
    try:
        from .sources.health import record_source_event

        record_source_event(
            source,
            success=success,
            latency_ms=(time.perf_counter() - started) * 1000,
            error=error,
        )
    except Exception:
        pass


class _MemoryCache:
    """Default in-process TTL cache (no external deps)."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}

    async def get(self, key: str) -> Optional[str]:
        item = self._store.get(key)
        if not item:
            return None
        ts, value = item
        if time.time() - ts > get_settings().cache_ttl_seconds:
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str) -> None:
        self._store[key] = (time.time(), value)

    async def close(self) -> None:
        # nothing to release for the in-process backend
        pass


class _RedisCache:
    """Async Redis backend using redis.asyncio.

    TTL is set per-key from ``Settings.cache_ttl_seconds``. Lazily connects on
    first use so the app boots fine when Redis is unreachable at import time.
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._redis = None
        self._lock = asyncio.Lock()

    async def _client(self):
        if self._redis is None:
            async with self._lock:
                if self._redis is None:
                    import redis.asyncio as aioredis  # local import: optional dep

                    self._redis = aioredis.from_url(
                        self._url, decode_responses=True
                    )
        return self._redis

    async def get(self, key: str) -> Optional[str]:
        try:
            client = await self._client()
            return await client.get(f"nakama:{key}")
        except Exception:
            # Redis down → behave as a cache miss rather than 500-ing the API.
            return None

    async def set(self, key: str, value: str) -> None:
        try:
            client = await self._client()
            ttl = get_settings().cache_ttl_seconds
            await client.set(f"nakama:{key}", value, ex=ttl)
        except Exception:
            # Swallow: a cache write failure must not break the request.
            pass

    async def close(self) -> None:
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None


def _build_cache():
    """Pick the cache backend based on current settings."""
    s = get_settings()
    if s.redis_url:
        return _RedisCache(s.redis_url)
    return _MemoryCache()


_cache = _build_cache()
_http: Optional[httpx.AsyncClient] = None
_lock = asyncio.Lock()


async def get_client(source: Optional[str] = None) -> httpx.AsyncClient:
    """Return a shared httpx client, optionally with proxy rotation.

    When ``source`` is given and a proxy is configured for it, the client
    routes through the proxy URL returned by ``proxy_rotation.next_proxy()``.
    If no proxy is configured, returns the shared singleton.

    Set ``PROXY_URL`` (global) or ``PROXY_URL_<SOURCE>`` (per-source) env vars
    to enable. Disable for specific sources with ``PROXY_DISABLE_FOR``.
    """
    global _http
    # Check if this source needs a proxy
    proxy = None
    if source:
        try:
            from .sources.proxy_rotation import next_proxy
            proxy = next_proxy(source)
        except Exception:
            proxy = None

    if proxy is not None:
        # Per-request: create a dedicated client with this proxy.
        # The pool will be reused by httpx internally within the client.
        return httpx.AsyncClient(
            proxy=proxy,
            follow_redirects=True,
            timeout=get_settings().request_timeout,
            headers={"User-Agent": get_settings().user_agent},
        )

    # No proxy: use the shared singleton
    if _http is None:
        async with _lock:
            if _http is None:
                _http = httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=get_settings().request_timeout,
                    headers={"User-Agent": get_settings().user_agent},
                )
    return _http


def _cache_key(method: str, url: str, params: Optional[dict], body: Optional[dict] = None) -> str:
    raw = f"{method}|{url}|{json.dumps(params or {})}|{json.dumps(body or {})}"
    return hashlib.sha1(raw.encode()).hexdigest()


def _fixture_path(url: str, suffix: str = ".html", body: Optional[dict] = None) -> Optional[str]:
    s = get_settings()
    if not s.offline_mode:
        return None
    # derive a deterministic filename: prefer hashing the same way _cache_key does
    raw = f"POST|{url}|{json.dumps({})}|{json.dumps(body or {})}" if body else f"GET|{url}|{json.dumps({})}"
    name = hashlib.sha1(raw.encode()).hexdigest()[:16] + suffix
    path = os.path.join(s.fixtures_dir, name)
    if os.path.exists(path):
        return path
    # Fallback: hash the raw URL (for GET fixtures without body)
    name = hashlib.sha1(url.encode()).hexdigest()[:16] + suffix
    path = os.path.join(s.fixtures_dir, name)
    return path if os.path.exists(path) else None


async def fetch_text(
    url: str,
    *,
    params: Optional[dict] = None,
    source: Optional[str] = None,
) -> str:
    """Fetch a URL as text, using cache + offline fixtures when configured.

    ``source`` is an optional label used for ``source_requests_total``; pass the
    source name (e.g. ``"otakudesu"``) to keep the metric useful for dashboards.
    """
    started = time.perf_counter()
    key = _cache_key("GET", url, params)
    cached = await _cache.get(key)
    if cached is not None:
        cache_hits_total.inc()
        _record(source, success=True, started=started)
        return cached
    cache_misses_total.inc()

    fp = _fixture_path(url)
    if fp:
        with open(fp, "r", encoding="utf-8") as fh:
            text = fh.read()
        await _cache.set(key, text)
        # Fixture reads count as source activity (200 OK). In offline mode this
        # is the only path exercised; counting fixtures keeps the metric
        # useful in tests and dev. The status is 200 because the fixture exists.
        if source:
            source_requests_total.labels(source=source, method="GET", status="200").inc()
        _record(source, success=True, started=started)
        return text

    await throttle_source(source)
    client = await get_client(source=source)
    resp = await client.get(url, params=params)
    status = str(resp.status_code)

    # Cloudflare / bot walls: optionally solve via FlareSolverr.
    if resp.status_code in (403, 503) and get_settings().flaresolverr_url:
        try:
            text = await _flaresolverr_get(url if not params else str(resp.url))
            if source:
                source_requests_total.labels(
                    source=source, method="GET", status="200"
                ).inc()
            await _cache.set(key, text)
            _record(source, success=True, started=started)
            return text
        except Exception as e:
            # Fall through to normal error mapping below.
            fs_err = str(e)
        else:
            fs_err = None
    else:
        fs_err = None

    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        if source:
            source_requests_total.labels(source=source, method="GET", status=status).inc()
        from .sources.base import SourceError

        msg = f"{source or 'upstream'} HTTP {resp.status_code} for {url}"
        if fs_err:
            msg = f"{msg} (flaresolverr: {fs_err[:120]})"
        _record(source, success=False, started=started, error=msg)
        raise SourceError(msg) from e
    else:
        if source:
            source_requests_total.labels(source=source, method="GET", status=status).inc()
    text = resp.text
    await _cache.set(key, text)
    _record(source, success=True, started=started)
    return text


async def fetch_soup(
    url: str,
    *,
    params: Optional[dict] = None,
    source: Optional[str] = None,
) -> BeautifulSoup:
    text = await fetch_text(url, params=params, source=source)
    return BeautifulSoup(text, "lxml")


async def _flaresolverr_get(url: str) -> str:
    """Solve a Cloudflare challenge via FlareSolverr and return HTML."""
    s = get_settings()
    if not s.flaresolverr_url:
        raise RuntimeError("FLARESOLVERR_URL not configured")
    client = await get_client()
    payload = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": 85000,
    }
    resp = await client.post(s.flaresolverr_url, json=payload, timeout=90.0)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "ok":
        raise RuntimeError(f"FlareSolverr failed: {data.get('message')}")
    sol = data.get("solution") or {}
    html = sol.get("response") or ""
    if not html:
        raise RuntimeError("FlareSolverr returned empty response")
    return html


async def fetch_json(
    url: str,
    *,
    params: Optional[dict] = None,
    suffix: str = ".json",
    headers: Optional[dict] = None,
    retry_429: bool = True,
    source: Optional[str] = None,
    method: str = "GET",
    json_body: Optional[dict] = None,
) -> dict:
    """Fetch a URL and parse the response as JSON.

    Honours OFFLINE_MODE by reading a fixture file (``<sha1>.json``) from the
    fixtures directory. When live, honours a 429 retry-after response with a
    short exponential backoff (used by rate-limited APIs such as MangaDex).

    ``source`` is an optional metric label forwarded to ``source_requests_total``.
    """
    started = time.perf_counter()
    key = _cache_key(method, url, params, body=json_body)
    cached = await _cache.get(key)
    if cached is not None:
        cache_hits_total.inc()
        _record(source, success=True, started=started)
        return json.loads(cached)
    cache_misses_total.inc()

    fp = _fixture_path(url, suffix=suffix, body=json_body)
    if fp:
        with open(fp, "r", encoding="utf-8") as fh:
            text = fh.read()
        await _cache.set(key, text)
        # Fixture reads count as source activity (200 OK). See fetch_text.
        if source:
            source_requests_total.labels(source=source, method=method, status="200").inc()
        _record(source, success=True, started=started)
        return json.loads(text)

    await throttle_source(source)
    client = await get_client(source=source)
    # One retry on 429 with a short backoff; MangaDex rate-limits at ~5/sec.
    resp = None
    for attempt in range(2):
        if attempt > 0:
            await throttle_source(source)
        if method == "POST":
            resp = await client.post(url, json=json_body, headers=headers)
        else:
            resp = await client.get(url, params=params, headers=headers)
        if (resp.status_code == 429 and retry_429 and attempt == 0) or (
            resp.status_code in (502, 503, 504) and attempt == 0
        ):
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", "1") or "1")
                await asyncio.sleep(min(retry_after, 2.0))
            else:
                await asyncio.sleep(2.0)
            continue
        status = str(resp.status_code)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if source:
                source_requests_total.labels(
                    source=source, method=method, status=status
                ).inc()
            from .sources.base import SourceError

            msg = f"{source or 'upstream'} HTTP {resp.status_code} for {url}"
            _record(source, success=False, started=started, error=msg)
            raise SourceError(msg) from e
        else:
            if source:
                source_requests_total.labels(
                    source=source, method=method, status=status
                ).inc()
        break
    assert resp is not None  # loop above always runs at least once
    text = resp.text
    await _cache.set(key, text)
    _record(source, success=True, started=started)
    return json.loads(text)


async def close_client() -> None:
    global _http
    if _http is not None:
        await _http.aclose()
        _http = None
    await _cache.close()
