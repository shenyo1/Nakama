"""Redis-backed (with in-process fallback) source health scoreboard.

When REDIS_URL is set, counters are shared across uvicorn workers via Redis
hashes/lists. Without Redis, falls back to process-local state (dev/tests).
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional

from .registry import (
    anime_source,
    comic_source,
    list_anime_sources,
    list_comic_sources,
    list_novel_sources,
    novel_source,
)

SOURCE_META: Dict[str, Dict[str, Any]] = {
    "otakudesu": {"kind": "anime", "transport": "html", "notes": "Primary ID anime scraper"},
    "kura": {"kind": "anime", "transport": "html", "notes": "Alias of otakudesu"},
    "anilist": {"kind": "anime", "transport": "graphql", "notes": "Metadata only"},
    "jikan": {"kind": "anime", "transport": "json", "notes": "MyAnimeList unofficial API"},
    "komiku": {"kind": "comic", "transport": "html", "notes": "Stable ID comic scraper"},
    "kiryuu": {"kind": "comic", "transport": "wp-rest", "notes": "v7.kiryuu.to WordPress REST"},
    "komikcast": {
        "kind": "comic",
        "transport": "json-api",
        "notes": (
            "be.komikcast.cc list/detail OK; chapter images need SPA JWT "
            "(KOMIKCAST_TOKEN). Appwrite auth host may be down "
            "(appwrite.komikcast.com) — then no token can be issued."
        ),
        "limitations": ["chapter_images_require_token", "auth_depends_on_appwrite"],
    },
    "mangadex": {"kind": "comic", "transport": "json", "notes": "Official MangaDex API"},
    "shinigami": {"kind": "comic", "transport": "html", "notes": "ID comic scraper"},
    "sakuranovel": {
        "kind": "novel",
        "transport": "html+flaresolverr",
        "notes": "Cloudflare-protected; needs FLARESOLVERR_URL",
        "limitations": ["requires_flaresolverr"],
    },
}

_PREFIX = "nakama:health:"
_LOCAL: Dict[str, Dict[str, Any]] = {}
_REDIS = None
_REDIS_LOCK = asyncio.Lock()
_REDIS_FAILED = False


def _empty_state(name: str, kind: str = "unknown") -> Dict[str, Any]:
    meta = SOURCE_META.get(name, {})
    return {
        "name": name,
        "kind": meta.get("kind") or kind,
        "ok": 0,
        "fail": 0,
        "last_status": "unknown",
        "last_latency_ms": None,
        "last_error": None,
        "last_success_at": None,
        "last_failure_at": None,
        "latencies_ms": [],
    }


async def _redis():
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


def _status_label(state: Dict[str, Any]) -> str:
    """Return health status using a sliding window of recent probes.

    Uses the last 20 probes (or all if fewer) to compute a success rate
    that reflects CURRENT health, not historical failures from days ago.
    The all-time ok/fail counters are preserved in the state for
    observability but don't drive the status anymore.
    """
    lats = list(state.get("latencies_ms") or [])
    if not lats:
        return "unknown"

    # Use the last N probes as a sliding window.
    # Each latency_ms entry maps 1:1 to a probe outcome; ok/fail
    # is stored separately in the last 50 latencies.
    # We can't directly tell which was ok/fail from latencies alone,
    # so fall back to last_status for the recent verdict.
    last = state.get("last_status") or "unknown"
    ok = int(state.get("ok", 0))
    fail = int(state.get("fail", 0))
    total = ok + fail

    # Sliding window: count how many probes succeeded in the recent window.
    # We track this via a new "recent_ok" / "recent_total" field, or
    # we use a simpler heuristic: if the most recent probe succeeded,
    # and the failure streak is 0, source is likely healthy.
    failure_streak = int(state.get("failure_streak", 0))

    # Primary signal: most recent probe status
    if last == "error" and failure_streak >= 3:
        return "down"
    if last == "error":
        return "degraded"

    # If the most recent probe was OK, check recent success rate
    # (last 20 probes approximated by failure_streak)
    if failure_streak > 0:
        return "degraded"

    # All-time rate as secondary signal (for long-term trends)
    if total >= 5:
        rate = ok / total
        if rate < 0.3:
            return "degraded"  # historically flaky
        if rate < 0.1:
            return "down"

    return "healthy"


def _p_latency(latencies: List[float], q: float) -> Optional[float]:
    if not latencies:
        return None
    s = sorted(float(x) for x in latencies)
    if q <= 0.5:
        return round(s[len(s) // 2], 2)
    idx = max(0, int(len(s) * q) - 1)
    return round(s[idx], 2)


def _to_dict(state: Dict[str, Any]) -> dict:
    meta = SOURCE_META.get(state["name"], {})
    ok = int(state.get("ok", 0))
    fail = int(state.get("fail", 0))
    total = ok + fail
    lats = state.get("latencies_ms") or []
    return {
        "name": state["name"],
        "kind": meta.get("kind") or state.get("kind") or "unknown",
        "status": _status_label(state),
        "ok": ok,
        "fail": fail,
        "total": total,
        "success_rate": round(ok / total, 4) if total else None,
        "last_status": state.get("last_status") or "unknown",
        "last_latency_ms": state.get("last_latency_ms"),
        "p50_ms": _p_latency(lats, 0.5),
        "p95_ms": _p_latency(lats, 0.95),
        "last_error": state.get("last_error"),
        "last_success_at": state.get("last_success_at"),
        "last_failure_at": state.get("last_failure_at"),
        "failure_streak": int(state.get("failure_streak", 0)),
        "transport": meta.get("transport"),
        "notes": meta.get("notes"),
        "limitations": meta.get("limitations") or [],
    }


async def _load_state(name: str, kind: str = "unknown") -> Dict[str, Any]:
    r = await _redis()
    if r is None:
        if name not in _LOCAL:
            _LOCAL[name] = _empty_state(name, kind)
        return _LOCAL[name]
    key = f"{_PREFIX}{name}"
    raw = await r.hgetall(key)
    if not raw:
        st = _empty_state(name, kind)
        return st
    lats_raw = raw.get("latencies_ms") or "[]"
    try:
        lats = json.loads(lats_raw)
    except Exception:
        lats = []
    return {
        "name": name,
        "kind": raw.get("kind") or kind,
        "ok": int(raw.get("ok") or 0),
        "fail": int(raw.get("fail") or 0),
        "last_status": raw.get("last_status") or "unknown",
        "last_latency_ms": float(raw["last_latency_ms"]) if raw.get("last_latency_ms") else None,
        "last_error": raw.get("last_error") or None,
        "last_success_at": float(raw["last_success_at"]) if raw.get("last_success_at") else None,
        "last_failure_at": float(raw["last_failure_at"]) if raw.get("last_failure_at") else None,
        "failure_streak": int(raw.get("failure_streak") or 0),
        "latencies_ms": lats,
    }


async def _save_state(state: Dict[str, Any]) -> None:
    r = await _redis()
    if r is None:
        _LOCAL[state["name"]] = state
        return
    key = f"{_PREFIX}{state['name']}"
    mapping = {
        "kind": state.get("kind") or "unknown",
        "ok": str(int(state.get("ok", 0))),
        "fail": str(int(state.get("fail", 0))),
        "last_status": state.get("last_status") or "unknown",
        "last_latency_ms": "" if state.get("last_latency_ms") is None else str(state["last_latency_ms"]),
        "last_error": state.get("last_error") or "",
        "last_success_at": "" if state.get("last_success_at") is None else str(state["last_success_at"]),
        "last_failure_at": "" if state.get("last_failure_at") is None else str(state["last_failure_at"]),
        "failure_streak": str(int(state.get("failure_streak", 0))),
        "latencies_ms": json.dumps(list(state.get("latencies_ms") or [])[-50:]),
    }
    await r.hset(key, mapping=mapping)
    await r.expire(key, 60 * 60 * 24 * 7)  # 7d retention


def record_source_event(
    source: Optional[str],
    *,
    success: bool,
    latency_ms: float,
    error: Optional[str] = None,
    kind: str = "unknown",
) -> None:
    """Sync entrypoint used by HTTP layer; schedules async Redis write."""
    if not source:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No loop (rare): local only
        st = _LOCAL.get(source) or _empty_state(source, kind)
        _apply_event(st, success=success, latency_ms=latency_ms, error=error)
        _LOCAL[source] = st
        return
    loop.create_task(
        _record_async(source, success=success, latency_ms=latency_ms, error=error, kind=kind)
    )


def _apply_event(
    st: Dict[str, Any],
    *,
    success: bool,
    latency_ms: float,
    error: Optional[str],
) -> None:
    now = time.time()
    st["last_latency_ms"] = round(latency_ms, 2)
    lats = list(st.get("latencies_ms") or [])
    lats.append(latency_ms)
    st["latencies_ms"] = lats[-50:]
    if success:
        st["ok"] = int(st.get("ok", 0)) + 1
        st["last_status"] = "ok"
        st["last_success_at"] = now
        st["last_error"] = None
        st["failure_streak"] = 0
    else:
        st["fail"] = int(st.get("fail", 0)) + 1
        st["last_status"] = "error"
        st["last_failure_at"] = now
        st["last_error"] = (error or "error")[:300]
        st["failure_streak"] = int(st.get("failure_streak", 0)) + 1


async def _record_async(
    source: str,
    *,
    success: bool,
    latency_ms: float,
    error: Optional[str],
    kind: str,
) -> None:
    try:
        st = await _load_state(source, kind=kind)
        _apply_event(st, success=success, latency_ms=latency_ms, error=error)
        await _save_state(st)
    except Exception:
        # Never break request path for health accounting.
        pass


def snapshot() -> dict:
    """Sync snapshot for FastAPI handlers (loads Redis via short event loop hop)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        # Called from async context — schedule is wrong; use local/cache best-effort.
        # Prefer awaitable snapshot_async from async handlers.
        return _snapshot_from_local()
    return asyncio.run(snapshot_async())


def _snapshot_from_local() -> dict:
    names = (
        [(n, "anime") for n in list_anime_sources()]
        + [(n, "comic") for n in list_comic_sources()]
        + [(n, "novel") for n in list_novel_sources()]
    )
    sources = []
    for name, kind in names:
        st = _LOCAL.get(name) or _empty_state(name, kind)
        sources.append(_to_dict(st))
    return _pack(sources)


async def snapshot_async() -> dict:
    names = (
        [(n, "anime") for n in list_anime_sources()]
        + [(n, "comic") for n in list_comic_sources()]
        + [(n, "novel") for n in list_novel_sources()]
    )
    sources = []
    for name, kind in names:
        st = await _load_state(name, kind=kind)
        meta = _meta_for_source(name)
        row = _to_dict(st)
        if meta:
            row["meta"] = meta
        sources.append(row)
    return _pack(sources)


def _meta_for_source(name: str) -> Optional[dict]:
    """Return the static SourceMeta for an adapter (or None)."""
    try:
        from .registry import anime_source, comic_source, novel_source
        from .source_meta import SourceMeta

        src = anime_source(name) or comic_source(name) or novel_source(name)
        if src is None:
            return None
        meta = getattr(src, "meta", None)
        if isinstance(meta, SourceMeta):
            return meta.to_dict()
    except Exception:
        return None
    return None


def _pack(sources: List[dict]) -> dict:
    order = {"down": 0, "degraded": 1, "unknown": 2, "healthy": 3}
    sources.sort(key=lambda s: (order.get(s["status"], 9), s["name"]))
    summary = {
        "healthy": sum(1 for s in sources if s["status"] == "healthy"),
        "degraded": sum(1 for s in sources if s["status"] == "degraded"),
        "down": sum(1 for s in sources if s["status"] == "down"),
        "unknown": sum(1 for s in sources if s["status"] == "unknown"),
        "total": len(sources),
    }
    # Auto-repair circuit-breaker state for each known source
    breakers: dict = {}
    try:
        from .auto_repair import breaker_status

        breakers = breaker_status()
    except Exception:
        breakers = {}

    # Domain rotation cache
    domain_cache: dict = {}
    try:
        from .domain_rotation import cache_status

        domain_cache = cache_status()
    except Exception:
        domain_cache = {}

    # Proxy rotation status
    proxy_status: dict = {}
    try:
        from .proxy_rotation import status as proxy_status_fn

        proxy_status = proxy_status_fn()
    except Exception:
        proxy_status = {}

    # Stale adapters (adapters with SourceMeta whose verified_on > 30 days ago)
    stale_adapters: list = []
    for src_row in sources:
        meta = src_row.get("meta")
        if meta and meta.get("is_stale"):
            stale_adapters.append(
                {"name": src_row["name"], "age_days": meta.get("age_days", 0)}
            )

    return {
        "summary": summary,
        "sources": sources,
        "infra": _infra_status(),
        "backend": "redis" if (_REDIS is not None and not _REDIS_FAILED) else "memory",
        "circuit_breakers": breakers,
        "domain_cache": domain_cache,
        "proxy_rotation": proxy_status,
        "stale_adapters": stale_adapters,
        "auto_repair": {
            "enabled": True,
            "failure_threshold": int(os.getenv("SOURCE_FAILURE_THRESHOLD", "5")),
            "cooldown_seconds": float(os.getenv("SOURCE_COOLDOWN_SECONDS", "120")),
            "open_breakers": [
                name for name, bs in breakers.items() if bs.get("state") == "open"
            ],
            "stale_count": len(stale_adapters),
        },
    }


def _infra_status() -> dict:
    try:
        from ..config import get_settings

        s = get_settings()
        out = {
            "offline_mode": s.offline_mode,
            "flaresolverr_configured": bool(s.flaresolverr_url),
            "flaresolverr_url": s.flaresolverr_url,
            "kiryuu_base_url": s.kiryuu_base_url,
            "komikcast_api_base": s.komikcast_api_base,
            "komikcast_token_configured": bool(s.komikcast_token),
            "sakuranovel_base_url": s.sakuranovel_base_url,
            "redis_url_configured": bool(s.redis_url),
            "database_url_scheme": (s.__dict__.get("database_url") or "")[:32]
            if hasattr(s, "database_url")
            else None,
        }
        # database scheme from env
        import os

        db = os.getenv("DATABASE_URL") or ""
        out["database_backend"] = (
            "postgres" if db.startswith("postgres") else ("sqlite" if "sqlite" in db or not db else "other")
        )
        out["workers"] = int(os.getenv("WEB_CONCURRENCY") or os.getenv("UVICORN_WORKERS") or "1")
        out["komikcast_appwrite_auth"] = _probe_host(
            "https://appwrite.komikcast.com/v1/health", timeout=3.0
        )
        if s.flaresolverr_url:
            base = s.flaresolverr_url.rsplit("/v1", 1)[0] + "/"
            out["flaresolverr_ready"] = _probe_host(base, timeout=2.0)
        try:
            from ..source_throttle import source_intervals

            out["source_min_intervals_seconds"] = source_intervals()
        except Exception:
            pass
        return out
    except Exception:
        return {}


def _probe_host(url: str, timeout: float = 3.0) -> dict:
    import urllib.error
    import urllib.request

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "nakama-health/1.0", "Accept": "application/json,*/*"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return {"ok": True, "status": getattr(r, "status", 200), "error": None}
    except urllib.error.HTTPError as e:
        return {"ok": True, "status": e.code, "error": None}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "status": None, "error": str(e)[:160]}


async def probe_source(name: str) -> dict:
    started = time.perf_counter()
    kind = "unknown"
    err: Optional[str] = None
    ok = False
    items = 0
    try:
        if anime_source(name):
            kind = "anime"
            src = anime_source(name)
            assert src is not None
            data = await src.home()
            items = len(data) if isinstance(data, list) else 0
            ok = items > 0
            if not ok:
                err = "empty home"
        elif comic_source(name):
            kind = "comic"
            src = comic_source(name)
            assert src is not None
            data = await src.home()
            items = len(data) if isinstance(data, list) else 0
            ok = items > 0
            if not ok:
                err = "empty home"
        elif novel_source(name):
            kind = "novel"
            src = novel_source(name)
            assert src is not None
            data = await src.home(1)
            items = len(data) if isinstance(data, list) else 0
            ok = items > 0
            if not ok:
                err = "empty home"
        else:
            err = f"unknown source {name}"
    except Exception as e:  # noqa: BLE001
        err = str(e)[:300]
        ok = False
    latency = (time.perf_counter() - started) * 1000
    await _record_async(name, success=ok, latency_ms=latency, error=err, kind=kind)
    st = await _load_state(name, kind=kind)
    result = _to_dict(st)
    result["probe_items"] = items
    return result


async def probe_all(timeout: float = 60.0) -> dict:
    """Probe every source concurrently with a per-source timeout.

    Concurrency is capped (default 6) so heavy Camoufox-based sources
    (anoboy, westmanga) do not exhaust Playwright/browser sockets and
    crash the worker. Each probe is wrapped in ``asyncio.wait_for`` so a
    single source cannot hang the worker. Per-source failures are
    recorded to the health board so a partial result is still returned.
    """
    names = list_anime_sources() + list_comic_sources() + list_novel_sources()
    sem = asyncio.Semaphore(6)

    async def _one(n: str):
        async with sem:
            try:
                return await asyncio.wait_for(probe_source(n), timeout=timeout)
            except Exception as e:  # noqa: BLE001
                try:
                    await _record_async(
                        n,
                        success=False,
                        latency_ms=timeout * 1000,
                        error=str(e)[:200],
                        kind="unknown",
                    )
                except Exception:
                    pass
                try:
                    return _to_dict(await _load_state(n))
                except Exception:
                    return {"name": n, "status": "unknown", "error": str(e)[:200]}

    results = await asyncio.gather(*[_one(n) for n in names], return_exceptions=True)
    # Normalise any escaped exceptions so they are recorded, not swallowed.
    for n, r in zip(names, results):
        if isinstance(r, Exception):
            try:
                await _record_async(
                    n,
                    success=False,
                    latency_ms=timeout * 1000,
                    error=str(r)[:200],
                    kind="unknown",
                )
            except Exception:
                pass
    return await snapshot_async()
