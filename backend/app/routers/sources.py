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
    """Test komikcast chapter-image endpoint accessibility.

    Returns {configured, valid, error, image_count_sample, last_checked,
    auth_required}.

    NOTE: komikcast's /series/{slug}/chapters/{index} endpoint currently does
    NOT require a valid bearer token for public series — any string (or no
    Authorization header at all) returns images. This check tests that the
    endpoint still returns images. If komikcast later enforces real auth,
    the `auth_required` field will flip to true and the operator must ensure
    KOMIKCAST_TOKEN contains a valid oat_* token.

    Uses a direct httpx call (NOT fetch_json) because fetch_json caches
    responses — a cached "valid=true" would hide endpoint changes for
    cache_ttl_seconds (default 900s).
    """
    import asyncio
    import time
    import httpx

    token = get_settings().komikcast_token
    now = time.time()
    test_slug = "ikiru-no-hetana-tako-no-joshi"

    # First: test WITHOUT token to see if endpoint is publicly accessible.
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp_noauth = await client.get(
                f"https://be.komikcast.cc/series/{test_slug}/chapters/1",
                headers={
                    "Origin": "https://v3.komikcast.fit",
                    "Referer": "https://v3.komikcast.fit/",
                    "Accept": "application/json",
                },
            )
        body_noauth = resp_noauth.json()
        noauth_ok = (
            isinstance(body_noauth, dict)
            and body_noauth.get("status") == 200
            and isinstance(
                (body_noauth.get("data") or {}).get("data", {}).get("images"),
                list,
            )
        )
    except Exception as e:
        return {
            "configured": bool(token),
            "valid": False,
            "error": f"no-auth probe failed: {type(e).__name__}: {str(e)[:150]}",
            "last_checked": now,
            "auth_required": None,
        }

    if noauth_ok:
        # Endpoint is publicly accessible — token not needed but still
        # report configured status for observability.
        images = body_noauth["data"]["data"]["images"]
        return {
            "configured": bool(token),
            "valid": True,
            "image_count_sample": len(images),
            "last_checked": now,
            "auth_required": False,
            "notes": "endpoint accepts no Authorization header; token not enforced",
        }

    # Endpoint rejected no-auth request — token is required. Test with token.
    if not token:
        return {
            "configured": False,
            "valid": False,
            "error": "endpoint requires auth but KOMIKCAST_TOKEN not set",
            "last_checked": now,
            "auth_required": True,
        }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"https://be.komikcast.cc/series/{test_slug}/chapters/1",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Origin": "https://v3.komikcast.fit",
                    "Referer": "https://v3.komikcast.fit/",
                    "Accept": "application/json",
                },
            )
        body = resp.json()
        if isinstance(body, dict) and body.get("status") == 200:
            data = body.get("data") or {}
            inner = data.get("data") if isinstance(data.get("data"), dict) else data
            images = inner.get("images") if isinstance(inner, dict) else None
            return {
                "configured": True,
                "valid": True,
                "image_count_sample": len(images) if isinstance(images, list) else 0,
                "last_checked": now,
                "auth_required": True,
            }
        return {
            "configured": True,
            "valid": False,
            "error": f"token rejected: status={body.get('status') if isinstance(body,dict) else 'n/a'} http={resp.status_code}",
            "last_checked": now,
            "auth_required": True,
        }
    except asyncio.TimeoutError:
        return {
            "configured": True,
            "valid": False,
            "error": "timeout (8s) — be.komikcast.cc unreachable",
            "last_checked": now,
            "auth_required": True,
        }
    except Exception as e:
        return {
            "configured": True,
            "valid": False,
            "error": f"{type(e).__name__}: {str(e)[:200]}",
            "last_checked": now,
            "auth_required": True,
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
