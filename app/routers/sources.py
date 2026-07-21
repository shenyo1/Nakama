"""Source health scoreboard endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from ..config import get_settings
from ..ratelimit import limiter
from ..schemas import ApiResponse
from ..sources.health import probe_all, probe_source, snapshot
from ..sources.registry import (
    list_anime_sources,
    list_comic_sources,
    list_novel_sources,
)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/health", response_model=ApiResponse, summary="Source health scoreboard")
@limiter.limit(get_settings().rate_limit)
async def sources_health(
    request: Request,
    probe: bool = Query(
        False,
        description="If true, actively probe every source home() (slow).",
    ),
):
    """Return per-source health from in-process counters.

    Without ``probe=true`` this is pure memory (fast). With ``probe=true`` the
    API hits each source's home listing once and updates the scoreboard.
    """
    if probe:
        data = await probe_all(timeout=20.0)
    else:
        data = snapshot()
    return ApiResponse(data=data)


@router.get(
    "/health/{name}",
    response_model=ApiResponse,
    summary="Probe a single source",
)
@limiter.limit(get_settings().rate_limit)
async def source_health_one(
    name: str,
    request: Request,
    probe: bool = Query(True, description="Actively probe this source (default true)."),
):
    known = set(list_anime_sources() + list_comic_sources() + list_novel_sources())
    if name not in known:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown source '{name}'. Available: {sorted(known)}",
        )
    if probe:
        data = await probe_source(name)
    else:
        # passive snapshot entry
        board = snapshot()
        data = next((s for s in board["sources"] if s["name"] == name), None)
        if data is None:
            raise HTTPException(status_code=404, detail=f"No health data for {name}")
    return ApiResponse(source=name, data=data)
