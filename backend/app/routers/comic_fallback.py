"""Comic fallback router: search/manga/chapter with auto-cross-source fallback.

Endpoints (all under /comic):

  GET /comic/search/{query}              — search across all comic sources
  GET /comic/manga/{slug}                — detail+chapters across comic sources
  GET /comic/chapter/{slug}              — first source with images wins

Each endpoint fans out concurrently across the comic source registry and:
- searches/details: aggregate results, surface per-source status
- chapter images: first non-empty image list wins; returns {source, data, sources_failed}

All three honor ``?primary=<source>`` to bias one source first (e.g. when the
caller already knows the upstream series is on a particular scraper).
"""
from __future__ import annotations
import asyncio
import re
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ..config import get_settings
from ..ratelimit import limiter
from ..schemas import ApiResponse
from ..sources import (
    comic_source,
    list_comic_sources,
    with_fallback,
)
from ..sources.base import SourceError

router = APIRouter(prefix="/comic-fallback", tags=["comic-fallback"])


@router.get("/search/{query}", summary="Search across comic sources with fallback")
@limiter.limit(get_settings().rate_limit)
async def fallback_search(
    request: Request,
    query: str,
    primary: Optional[str] = Query(
        None,
        description="Bias this source first (e.g. 'kiryuu'). Must be a known comic source.",
    ),
):
    primary = primary or "komiku"
    if primary not in list_comic_sources():
        raise HTTPException(
            status_code=404,
            detail=f"Unknown primary '{primary}'. Available: {list_comic_sources()}",
        )

    # Cache search results for 5 min to avoid re-fanning-out on repeated queries.
    # Comic search results change slowly; 5 min keeps response snappy without
    # stale results during typical browsing.
    from ..response_cache import cached_response

    async def _fetch():
        import time as _time
        _fetch_start = _time.perf_counter()
        # Per-source timeout (seconds). Most comic sources complete <1s;
        # 5s is a generous ceiling — sources that need more are usually
        # down anyway and Semaphore(6) limits blast radius.
        PER_SOURCE_TIMEOUT = 5.0
        # Max concurrent sources. Matches probe_all (option 6) which fixed
        # the v2.6.2 502 cascade. Concurrency >6 overwhelms Camoufox/FS.
        MAX_CONCURRENT = 6
        # Early-return threshold: as soon as this many sources have returned
        # successfully, return immediately. Remaining sources still run in
        # background to populate cache for next request.
        EARLY_OK = 3

        names = [primary] + [n for n in list_comic_sources() if n != primary]

        sem = asyncio.Semaphore(MAX_CONCURRENT)
        # Track which sources we've kicked off as background tasks so we can
        # attach results to the in-memory cache when they finish.
        in_flight: Dict[str, asyncio.Task] = {}
        # Track which sources returned successfully — used for early-return.
        ok_count = 0
        early_return = False

        async def _one(name: str, delay: float = 0.0) -> tuple[str, Any]:
            nonlocal ok_count
            if delay > 0:
                await asyncio.sleep(delay)
            async with sem:
                src = comic_source(name)
                if src is None:
                    return name, {"error": f"unknown comic source '{name}'"}
                try:
                    _t0 = time.perf_counter()
                    res = await asyncio.wait_for(src.search(query), timeout=PER_SOURCE_TIMEOUT)
                    _dur_ms = (time.perf_counter() - _t0) * 1000
                    # Emit per-source latency for /analytics dashboard.
                    try:
                        from ..routers.analytics import note_source_latency
                        note_source_latency(src.name, _dur_ms)
                    except Exception:
                        pass
                    return name, res
                except asyncio.TimeoutError:
                    return name, {"error": f"timeout after {PER_SOURCE_TIMEOUT}s"}
                except SourceError as e:
                    return name, {"error": str(e)}
                except Exception as e:  # noqa: BLE001
                    return name, {"error": f"{type(e).__name__}: {e}"}

        # Kick off all tasks. Each task is awaited with a wrapper that lets
        # us collect results as soon as they complete (for early-return).
        async def _track(t: asyncio.Task) -> tuple[str, Any]:
            nonlocal ok_count
            name, payload = await t
            if isinstance(payload, list):
                ok_count += 1
            return name, payload

        # Stagger slow sources by 0.3s to reduce thundering-herd on shared
        # infra (Camoufox session, FS pool).
        SLOW = {"komikcast", "westmanga"}  # comic sources that need extra infra
        tasks = []
        for n in names:
            if n in SLOW:
                tasks.append(asyncio.create_task(_one(n, 0.3)))
            else:
                tasks.append(asyncio.create_task(_one(n)))

        # Wait for tasks in completion order. Once EARLY_OK sources have
        # returned successfully, we have enough to build a useful response.
        # Remaining tasks are NOT cancelled — they keep running so the
        # response cache fills up for the next caller.
        finished: List[tuple[str, Any]] = []
        pending = set(tasks)
        try:
            while pending:
                done, pending = await asyncio.wait(
                    pending, timeout=PER_SOURCE_TIMEOUT, return_when=asyncio.FIRST_COMPLETED
                )
                if not done:
                    break  # all remaining tasks timed out
                for t in done:
                    finished.append(await _track(t))
                if ok_count >= EARLY_OK and not early_return:
                    early_return = True
                    break
        finally:
            # Cancel remaining tasks (they may have started already); we
            # don't need to wait for them since we already have enough
            # results to respond. They'll be re-fetched on next request.
            for t in pending:
                t.cancel()

        # If we early-returned with fewer than all sources, kick off the
        # remaining tasks and await them — this is the original behavior
        # path (gather all). It only triggers if EARLY_OK was never reached.
        if not early_return:
            # Drain anything still pending (shouldn't happen if early_return
            # was set, but defensive).
            for t in pending:
                try:
                    finished.append(await _track(t))
                except Exception:
                    pass

        # Build merged view from whichever sources we got.
        by_source: Dict[str, Any] = {}
        failed: List[Dict[str, str]] = []
        counts: Dict[str, int] = {}
        for name, payload in finished:
            if isinstance(payload, dict) and "error" in payload and len(payload) == 1:
                failed.append({"source": name, "error": str(payload["error"])})
                continue
            by_source[name] = payload
            counts[name] = len(payload) if isinstance(payload, list) else 0
        total = sum(counts.values())

        # Build deduplicated union of results, scored by source coverage.
        from ..sources.merge_search import normalize_title
        merged: Dict[str, dict] = {}
        for name, items in by_source.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = item.get("title") or item.get("name") or ""
                key = normalize_title(title)
                if not key:
                    continue
                if key not in merged:
                    merged[key] = {**item, "_sources": [], "_source_count": 0}
                merged[key]["_sources"].append(name)
                merged[key]["_source_count"] = len(merged[key]["_sources"])
        merged_list = sorted(
            merged.values(),
            key=lambda x: (-x.get("_source_count", 0), x.get("title", "")),
        )

        # Record search latency for /analytics dashboard (inside _fetch so
        # we have access to by_source + names; only runs on cache miss
        # because cached_response short-circuits cache hits before _fetch).
        try:
            from ..routers.analytics import note_search_latency
            _duration_ms = (time.perf_counter() - _fetch_start) * 1000
            ok_count = sum(1 for v in by_source.values() if isinstance(v, list))
            note_search_latency("comic", query, _duration_ms, ok_count, len(names))
        except Exception:
            pass

        return ApiResponse(
            data={
                "query": query,
                "primary": primary,
                "sources_tried": names,
                "sources_tried_count": len(names),
                "sources_completed": len(finished),
                "sources_failed": failed,
                "counts": counts,
                "total": total,
                "results": by_source,
                "merged": merged_list,
                "merged_unique_titles": len(merged),
                "early_return": early_return,
            },
        )

    return await cached_response(request, _fetch, ttl_seconds=300)


@router.get(
    "/manga/{slug:path}",
    summary="Find manga detail across comic sources with fallback",
)
@limiter.limit(get_settings().rate_limit)
async def fallback_manga(
    request: Request,
    slug: str,
    primary: Optional[str] = Query(None),
):
    primary = primary or "komiku"
    if primary not in list_comic_sources():
        raise HTTPException(
            status_code=404,
            detail=f"Unknown primary '{primary}'. Available: {list_comic_sources()}",
        )

    names = [primary] + [n for n in list_comic_sources() if n != primary]

    async def _one(name: str) -> tuple[str, Any]:
        src = comic_source(name)
        if src is None:
            return name, {"error": f"unknown comic source '{name}'"}
        try:
            return name, await src.manga(slug)
        except SourceError as e:
            return name, {"error": str(e)}
        except Exception as e:  # noqa: BLE001
            return name, {"error": f"{type(e).__name__}: {e}"}

    results = await asyncio.gather(*[_one(n) for n in names], return_exceptions=False)
    success: List[tuple[str, Any]] = []
    failed: List[Dict[str, str]] = []
    for name, payload in results:
        if isinstance(payload, dict) and "error" in payload and len(payload) == 1:
            failed.append({"source": name, "error": str(payload["error"])})
        else:
            success.append((name, payload))
    if success:
        winner_name, winner_data = success[0]
        return ApiResponse(
            source=winner_name,
            data={
                "primary": primary,
                "winner": winner_name,
                "detail": winner_data,
                "sources_failed": failed,
                "matched": len(success),
            },
        )
    raise HTTPException(
        status_code=502,
        detail=f"manga '{slug}' not found in any comic source. Last errors: "
        + "; ".join(f"{f['source']}: {f['error'][:80]}" for f in failed[-3:]),
    )


_SLUG_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


@router.get(
    "/chapter/{slug:path}",
    summary="Chapter images across comic sources with fallback",
)
@limiter.limit(get_settings().rate_limit)
async def fallback_chapter(
    request: Request,
    slug: str,
    primary: Optional[str] = Query(None),
):
    """First source returning a non-empty ``images`` list wins.

    Komikcast (which needs a JWT) is intentionally last so other free sources
    can serve images first.
    """
    sources = list_comic_sources()
    primary = primary or "komiku"
    if primary not in sources:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown primary '{primary}'. Available: {sources}",
        )
    # Order: primary, then others, but komikcast last (auth-gated).
    others = [n for n in sources if n != primary and n != "komikcast"]
    if primary != "komikcast":
        names = [primary] + others + ["komikcast"]
    else:
        names = ["komikcast"] + others

    async def _one(name: str) -> tuple[str, Any]:
        src = comic_source(name)
        if src is None:
            return name, {"error": "unknown"}
        try:
            return name, await src.chapter(slug)
        except SourceError as e:
            return name, {"error": str(e)}
        except Exception as e:  # noqa: BLE001
            return name, {"error": f"{type(e).__name__}: {e}"}

    results = await asyncio.gather(*[_one(n) for n in names], return_exceptions=False)
    failed: List[Dict[str, str]] = []
    for name, payload in results:
        if isinstance(payload, dict) and "error" in payload and len(payload) == 1:
            failed.append({"source": name, "error": str(payload["error"])})
            continue
        imgs = payload.get("images") if isinstance(payload, dict) else None
        if imgs:
            return ApiResponse(
                source=name,
                data={
                    "winner": name,
                    "image_count": len(imgs),
                    "primary": primary,
                    "chapter": payload,
                    "sources_failed": failed,
                },
            )
    # No images anywhere — return best metadata we have (first non-error).
    last_meta: Optional[tuple[str, Any]] = None
    for name, payload in results:
        if not (isinstance(payload, dict) and "error" in payload and len(payload) == 1):
            last_meta = (name, payload)
            break
    if last_meta:
        name, payload = last_meta
        return ApiResponse(
            source=name,
            data={
                "winner": None,
                "image_count": 0,
                "primary": primary,
                "chapter": payload,
                "sources_failed": failed,
                "notes": "No source returned images; got metadata only. "
                "Use /sources/health to inspect.",
            },
        )
    raise HTTPException(
        status_code=502,
        detail="chapter not found in any comic source. Last errors: "
        + "; ".join(f"{f['source']}: {f['error'][:80]}" for f in failed[-3:]),
    )