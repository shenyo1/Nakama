"""Ops analytics: cache headers, process cost guard, recent CF status samples."""
from __future__ import annotations

import os
import time
from collections import deque
from typing import Deque, Dict, Optional

from fastapi import APIRouter, Request

from ..config import get_settings
from ..ratelimit import limiter
from ..schemas import ApiResponse

router = APIRouter(tags=["ops"])

# In-process samples of CF cache status observed by synthetic uptime (optional)
# and a simple request counter for cost guard estimates.
_CF_SAMPLES: Deque[dict] = deque(maxlen=200)
_REQ_WINDOW: Deque[float] = deque(maxlen=5000)
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


@router.get("/analytics", response_model=ApiResponse, summary="Cache + cost guard analytics")
@limiter.limit(get_settings().rate_limit)
async def analytics(request: Request):
    """Lightweight ops analytics for Tier 3.

    * request rate (last 60s / 5m) from this process
    * CF cache status histogram from recent samples (if any)
    * process uptime / worker count / memory if available
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
        }
    )
