"""Source health scoreboard endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from ..config import get_settings
from ..ratelimit import limiter
from ..schemas import ApiResponse
from ..sources.health import probe_all, probe_source, snapshot_async
from ..sources.registry import (
    list_anime_sources,
    list_comic_sources,
    list_novel_sources,
)

router = APIRouter(prefix="/sources", tags=["sources"])


async def _check_komikcast_token() -> dict:
    """Test KOMIKCAST_TOKEN validity by hitting a token-gated endpoint.

    Returns {configured, valid, error, last_checked}.
    """
    import asyncio
    import time
    from ..http import fetch_json

    token = get_settings().komikcast_token
    now = time.time()
    if not token:
        return {
            "configured": False,
            "valid": False,
            "error": "KOMIKCAST_TOKEN not set; chapter images will return empty",
            "last_checked": now,
        }
    # Use a known public series + chapter index 1 to test token.
    # /series/{slug}/chapters/{index} requires bearer auth.
    test_slug = "ikiru-no-hetana-tako-no-joshi"
    try:
        body = await asyncio.wait_for(
            fetch_json(
                f"https://be.komikcast.cc/series/{test_slug}/chapters/1",
                source="komikcast",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Origin": "https://v3.komikcast.fit",
                    "Referer": "https://v3.komikcast.fit/",
                    "Accept": "application/json",
                },
            ),
            timeout=8.0,
        )
        if isinstance(body, dict) and body.get("status") == 200:
            data = body.get("data") or {}
            inner = data.get("data") if isinstance(data.get("data"), dict) else data
            images = inner.get("images") if isinstance(inner, dict) else None
            return {
                "configured": True,
                "valid": True,
                "image_count_sample": len(images) if isinstance(images, list) else 0,
                "last_checked": now,
            }
        return {
            "configured": True,
            "valid": False,
            "error": f"unexpected response: status={body.get('status') if isinstance(body,dict) else 'n/a'}",
            "last_checked": now,
        }
    except asyncio.TimeoutError:
        return {
            "configured": True,
            "valid": False,
            "error": "timeout (8s) — be.komikcast.cc unreachable or token expired",
            "last_checked": now,
        }
    except Exception as e:
        return {
            "configured": True,
            "valid": False,
            "error": f"{type(e).__name__}: {str(e)[:200]}",
            "last_checked": now,
        }


@router.get("/health", response_model=ApiResponse, summary="Source health scoreboard")
@limiter.limit(get_settings().rate_limit)
async def sources_health(
    request: Request,
    probe: bool = Query(
        False,
        description="If true, actively probe every source home() (slow).",
    ),
):
    """Return per-source health from Redis/memory counters.

    Without ``probe=true`` this is pure counter reads (fast). With
    ``probe=true`` the API hits each source home once and updates the board.

    Response also includes ``token_health`` for sources that require bearer
    auth (currently komikcast). This lets dashboards flag expired tokens
    before users hit empty chapter image lists.
    """
    if probe:
        data = await probe_all(timeout=20.0)
    else:
        data = await snapshot_async()
    # Always include komikcast token validity check (cheap: 1 HTTP call, ~200ms)
    data["token_health"] = {"komikcast": await _check_komikcast_token()}
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
        board = await snapshot_async()
        data = next((s for s in board["sources"] if s["name"] == name), None)
        if data is None:
            raise HTTPException(status_code=404, detail=f"No health data for {name}")
    # For komikcast, also include token health
    if name == "komikcast":
        data["token_health"] = await _check_komikcast_token()
    return ApiResponse(source=name, data=data)
