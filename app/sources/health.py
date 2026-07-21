"""In-process source health scoreboard.

Tracks per-source success/failure, latency, last error, and capability flags.
Used by ``GET /sources/health`` and optional active probes. Pure process state —
resets on restart (which is fine for ops dashboards; Prometheus retains history).
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .registry import (
    anime_source,
    comic_source,
    list_anime_sources,
    list_comic_sources,
    list_novel_sources,
    novel_source,
)


# Static capability notes so clients know what each source can do.
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


@dataclass
class SourceHealth:
    name: str
    kind: str = "unknown"
    ok: int = 0
    fail: int = 0
    last_status: str = "unknown"  # ok | error | unknown
    last_latency_ms: Optional[float] = None
    last_error: Optional[str] = None
    last_success_at: Optional[float] = None
    last_failure_at: Optional[float] = None
    latencies_ms: List[float] = field(default_factory=list)

    def record(self, *, success: bool, latency_ms: float, error: Optional[str] = None) -> None:
        now = time.time()
        self.last_latency_ms = round(latency_ms, 2)
        self.latencies_ms.append(latency_ms)
        if len(self.latencies_ms) > 50:
            self.latencies_ms = self.latencies_ms[-50:]
        if success:
            self.ok += 1
            self.last_status = "ok"
            self.last_success_at = now
            self.last_error = None
        else:
            self.fail += 1
            self.last_status = "error"
            self.last_failure_at = now
            self.last_error = (error or "error")[:300]

    @property
    def total(self) -> int:
        return self.ok + self.fail

    @property
    def success_rate(self) -> Optional[float]:
        if self.total == 0:
            return None
        return round(self.ok / self.total, 4)

    @property
    def p50_ms(self) -> Optional[float]:
        if not self.latencies_ms:
            return None
        s = sorted(self.latencies_ms)
        return round(s[len(s) // 2], 2)

    @property
    def p95_ms(self) -> Optional[float]:
        if not self.latencies_ms:
            return None
        s = sorted(self.latencies_ms)
        idx = max(0, int(len(s) * 0.95) - 1)
        return round(s[idx], 2)

    def status_label(self) -> str:
        """healthy | degraded | down | unknown"""
        if self.total == 0:
            return "unknown"
        if self.last_status == "error" and self.fail >= 2 and self.ok == 0:
            return "down"
        if self.last_status == "error":
            return "degraded"
        rate = self.success_rate or 0
        if rate >= 0.9:
            return "healthy"
        if rate >= 0.5:
            return "degraded"
        return "down"

    def to_dict(self) -> dict:
        meta = SOURCE_META.get(self.name, {})
        return {
            "name": self.name,
            "kind": meta.get("kind") or self.kind,
            "status": self.status_label(),
            "ok": self.ok,
            "fail": self.fail,
            "total": self.total,
            "success_rate": self.success_rate,
            "last_status": self.last_status,
            "last_latency_ms": self.last_latency_ms,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "last_error": self.last_error,
            "last_success_at": self.last_success_at,
            "last_failure_at": self.last_failure_at,
            "transport": meta.get("transport"),
            "notes": meta.get("notes"),
            "limitations": meta.get("limitations") or [],
        }


_LOCK = asyncio.Lock()
_STATE: Dict[str, SourceHealth] = {}


def _ensure(name: str, kind: str = "unknown") -> SourceHealth:
    if name not in _STATE:
        meta = SOURCE_META.get(name, {})
        _STATE[name] = SourceHealth(name=name, kind=meta.get("kind") or kind)
    return _STATE[name]


def record_source_event(
    source: Optional[str],
    *,
    success: bool,
    latency_ms: float,
    error: Optional[str] = None,
    kind: str = "unknown",
) -> None:
    if not source:
        return
    h = _ensure(source, kind=kind)
    h.record(success=success, latency_ms=latency_ms, error=error)


def snapshot() -> dict:
    """Return full scoreboard for all registered sources."""
    names = (
        [(n, "anime") for n in list_anime_sources()]
        + [(n, "comic") for n in list_comic_sources()]
        + [(n, "novel") for n in list_novel_sources()]
    )
    sources = []
    for name, kind in names:
        h = _ensure(name, kind=kind)
        sources.append(h.to_dict())
    # sort: down first, then degraded, healthy, unknown
    order = {"down": 0, "degraded": 1, "unknown": 2, "healthy": 3}
    sources.sort(key=lambda s: (order.get(s["status"], 9), s["name"]))
    summary = {
        "healthy": sum(1 for s in sources if s["status"] == "healthy"),
        "degraded": sum(1 for s in sources if s["status"] == "degraded"),
        "down": sum(1 for s in sources if s["status"] == "down"),
        "unknown": sum(1 for s in sources if s["status"] == "unknown"),
        "total": len(sources),
    }
    return {
        "summary": summary,
        "sources": sources,
        "infra": _infra_status(),
    }


def _infra_status() -> dict:
    """Infra flags + cheap upstream auth reachability (best-effort, no auth)."""
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
        }
        # Best-effort TCP/HTTP probe for Komikcast Appwrite auth host.
        # Does not use secrets; only reports whether auth backend is reachable.
        out["komikcast_appwrite_auth"] = _probe_host(
            "https://appwrite.komikcast.com/v1/health",
            timeout=3.0,
        )
        if s.flaresolverr_url:
            # readiness of local FlareSolverr (same network as API)
            base = s.flaresolverr_url.rsplit("/v1", 1)[0] + "/"
            out["flaresolverr_ready"] = _probe_host(base, timeout=2.0)
        return out
    except Exception:
        return {}


def _probe_host(url: str, timeout: float = 3.0) -> dict:
    """Return {ok, status, error} without raising."""
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
        # HTTP response means host is up (even 401/404)
        return {"ok": True, "status": e.code, "error": None}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "status": None, "error": str(e)[:160]}


async def probe_source(name: str) -> dict:
    """Active health probe: call home/search lightly and record outcome."""
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
    record_source_event(name, success=ok, latency_ms=latency, error=err, kind=kind)
    result = _ensure(name, kind=kind).to_dict()
    result["probe_items"] = items
    return result


async def probe_all(timeout: float = 25.0) -> dict:
    """Probe every registered source concurrently (bounded)."""
    names = list_anime_sources() + list_comic_sources() + list_novel_sources()

    async def _one(n: str):
        try:
            return await asyncio.wait_for(probe_source(n), timeout=timeout)
        except Exception as e:  # noqa: BLE001
            record_source_event(n, success=False, latency_ms=timeout * 1000, error=str(e)[:200])
            return _ensure(n).to_dict()

    await asyncio.gather(*[_one(n) for n in names])
    return snapshot()
