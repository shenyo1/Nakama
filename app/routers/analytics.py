"""Ops analytics: cache headers, process cost guard, recent CF status samples,
source performance, search latency tracking, and quota utilization."""
from __future__ import annotations

import os
import time
from collections import deque
from typing import Any, Deque, Dict, Optional

from fastapi import APIRouter, Request

from ..config import get_settings
from ..quota import PLAN_QUOTAS
from ..ratelimit import limiter
from ..schemas import ApiResponse
from ..response_cache import cache_stats

router = APIRouter(tags=["ops"])

# In-process samples of CF cache status observed by synthetic uptime (optional)
# and a simple request counter for cost guard estimates.
_CF_SAMPLES: Deque[dict] = deque(maxlen=200)
_REQ_WINDOW: Deque[float] = deque(maxlen=5000)
_SEARCH_LATENCY: Deque[dict] = deque(maxlen=100)
_SOURCE_LATENCY: Dict[str, Deque[float]] = {}
_STARTED = time.monotonic()


def note_cf_status(target: str, status: str, code: str = "200") -> None:
    _CF_SAMPLES.append(
        {
            "ts": time.time(),
            "target": target,
            "cf_cache_status": status,
            "code": code,
        }
    )


def note_request() -> None:
    _REQ_WINDOW.append(time.monotonic())


def note_search_latency(kind: str, query: str, duration_ms: float, sources_ok: int, sources_total: int) -> None:
    """Track search endpoint latency for analytics."""
    _SEARCH_LATENCY.append({
        "ts": time.time(),
        "kind": kind,
        "query": query[:50],
        "duration_ms": round(duration_ms, 1),
        "sources_ok": sources_ok,
        "sources_total": sources_total,
    })


def note_source_latency(source: str, duration_ms: float) -> None:
    """Track per-source fetch latency."""
    if source not in _SOURCE_LATENCY:
        _SOURCE_LATENCY[source] = deque(maxlen=50)
    _SOURCE_LATENCY[source].append(duration_ms)


@router.get("/analytics", response_model=ApiResponse, summary="Cache + cost guard analytics")
@limiter.limit(get_settings().rate_limit)
async def analytics(request: Request):
    """Lightweight ops analytics for Tier 3.

    * request rate (last 60s / 5m) from this process
    * CF cache status histogram from recent samples (if any)
    * process uptime / worker count / memory if available
    * search latency stats (p50, p95, p99)
    * per-source latency stats
    * cache backend stats
    * quota tier overview
    """
    note_request()
    now = time.monotonic()
    # prune is automatic via maxlen; count recent
    last_60 = sum(1 for t in _REQ_WINDOW if now - t <= 60)
    last_300 = sum(1 for t in _REQ_WINDOW if now - t <= 300)

    cf_hist: Dict[str, int] = {}
    for s in _CF_SAMPLES:
        k = s.get("cf_cache_status") or "unknown"
        cf_hist[k] = cf_hist.get(k, 0) + 1

    mem = {}
    try:
        # cgroup / proc memory (best-effort)
        with open("/proc/self/status", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:") or line.startswith("VmSize:"):
                    parts = line.split()
                    mem[parts[0].rstrip(":")] = f"{parts[1]} {parts[2]}"
    except OSError:
        pass

    loadavg = None
    try:
        loadavg = os.getloadavg()
    except OSError:
        pass

    workers = int(os.getenv("WEB_CONCURRENCY") or os.getenv("UVICORN_WORKERS") or "1")
    # Rough cost guard: if > 70% of a 2-core box on loadavg[0]
    cores = os.cpu_count() or 1
    load1 = loadavg[0] if loadavg else 0.0
    load_ratio = load1 / max(cores, 1)
    cost_guard = {
        "load1": load1,
        "cores": cores,
        "load_ratio": round(load_ratio, 3),
        "alert": load_ratio >= 0.7,
        "message": (
            "CPU load high — consider reducing scrape concurrency / raising cache TTL"
            if load_ratio >= 0.7
            else "ok"
        ),
    }

    # Search latency stats
    search_stats: Dict[str, Any] = {}
    if _SEARCH_LATENCY:
        durations = sorted([s["duration_ms"] for s in _SEARCH_LATENCY])
        search_stats = {
            "samples": len(durations),
            "p50_ms": durations[len(durations) // 2],
            "p95_ms": durations[int(len(durations) * 0.95)] if len(durations) > 1 else durations[0],
            "p99_ms": durations[int(len(durations) * 0.99)] if len(durations) > 2 else durations[-1],
            "avg_ms": round(sum(durations) / len(durations), 1),
            "recent": list(_SEARCH_LATENCY)[-10:],
        }

    # Per-source latency stats
    source_latency: Dict[str, Dict[str, float]] = {}
    for src, latencies in _SOURCE_LATENCY.items():
        if not latencies:
            continue
        vals = sorted(latencies)
        source_latency[src] = {
            "samples": len(vals),
            "p50_ms": round(vals[len(vals) // 2], 1),
            "p95_ms": round(vals[int(len(vals) * 0.95)] if len(vals) > 1 else vals[0], 1),
            "avg_ms": round(sum(vals) / len(vals), 1),
        }

    return ApiResponse(
        data={
            "uptime_seconds": round(now - _STARTED, 2),
            "workers": workers,
            "requests": {
                "last_60s": last_60,
                "last_5m": last_300,
                "window_size": len(_REQ_WINDOW),
            },
            "cf_cache_status_histogram": cf_hist,
            "cf_samples": list(_CF_SAMPLES)[-20:],
            "memory": mem,
            "cost_guard": cost_guard,
            "cache_policy": {
                "anime_comic_max_age": 60,
                "novel_max_age": 120,
                "search_max_age": 30,
                "health_no_store": True,
            },
            "cache_backend": cache_stats(),
            "search_latency": search_stats,
            "source_latency": source_latency,
            "quota_tiers": {
                plan: limit for plan, limit in PLAN_QUOTAS.items()
            },
        }
    )


@router.get("/analytics/search", response_model=ApiResponse, summary="Search performance breakdown")
@limiter.limit(get_settings().rate_limit)
async def search_analytics(request: Request):
    """Detailed search performance analytics.

    Shows latency distribution by kind (anime/comic/novel),
    slowest queries, and cache hit ratio for search endpoints.
    """
    note_request()
    by_kind: Dict[str, list] = {}
    for s in _SEARCH_LATENCY:
        k = s.get("kind", "unknown")
        by_kind.setdefault(k, []).append(s)

    kind_stats: Dict[str, dict] = {}
    for kind, samples in by_kind.items():
        durations = sorted([s["duration_ms"] for s in samples])
        kind_stats[kind] = {
            "count": len(samples),
            "p50_ms": durations[len(durations) // 2] if durations else 0,
            "p95_ms": durations[int(len(durations) * 0.95)] if len(durations) > 1 else (durations[0] if durations else 0),
            "avg_ms": round(sum(durations) / len(durations), 1) if durations else 0,
            "slowest": sorted(samples, key=lambda x: -x["duration_ms"])[:5],
        }

    return ApiResponse(data={
        "by_kind": kind_stats,
        "total_samples": len(_SEARCH_LATENCY),
    })
