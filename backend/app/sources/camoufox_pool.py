"""Shared Camoufox browser pool — single persistent browser instance.

Background:
- AsyncCamoufox launches a headless Firefox each time it's instantiated
- Browser launch takes 5-10s of overhead per request
- westmanga + sakuranovel + anoboy all use Camoufox for JS rendering
- Naively, each request creates a new browser = 15-45s per multi-source

This module provides a simple pool that:
- Lazily starts ONE browser on first use (not per-request)
- Tracks concurrent users with a semaphore (max 2 pages at once, since
  Firefox is heavyweight and launching more = OOM or hangs)
- Auto-restarts on crash with module-level lock
- 5-min idle timeout closes unused browser to free memory

USAGE:
  from app.sources.camoufox_pool import fetch_via_camoufox
  html = await fetch_via_camoufox(url, timeout=30)

`fetch_via_camoufox(url)` is a drop-in replacement for the old
`_fetch_with_camoufox(url)` function in westmanga.py, sakuranovel.py,
and anoboy.py — and saves 5-10s per request by reusing the browser.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Module-level state — process-wide singleton browser.
_browser: Optional[Any] = None  # AsyncCamoufox instance (launched)
_browser_obj: Optional[Any] = None  # The underlying playwright Browser object
_lock = asyncio.Lock()
_last_used: float = 0.0
_idle_timeout_s = 300  # close after 5min idle
_total_launches: int = 0
_concurrent_users: int = 0

# Cap concurrent pages per browser. Firefox can handle a few, but each
# page is ~150MB RSS; cap to prevent OOM on shared VPS.
_sem = asyncio.Semaphore(2)

DISABLED = False  # Set True via env (e.g. for tests/offline mode)


async def fetch_via_camoufox(url: str, timeout: int = 30) -> Optional[str]:
    """Fetch a URL using a shared Camoufox browser.

    Returns the rendered HTML string, or None on failure (caller can
    fall back to other strategies like FlareSolverr).
    """
    global _concurrent_users, _last_used

    if DISABLED:
        return None

    async with _sem:  # bound concurrent pages
        _concurrent_users += 1
        try:
            await _ensure_browser()
            _last_used = time.time()
            page = await _browser_obj.new_page()
            try:
                await page.goto(url, timeout=timeout * 1000)
                # Settle JS-rendered DOM. 3s covers most static + JS apps.
                await asyncio.sleep(3)
                return await page.content()
            finally:
                try:
                    await page.close()
                except Exception:
                    pass
        except Exception as e:
            # Mark browser as dead so next call launches a fresh one
            logger.warning(f"camoufox fetch failed: {e}")
            await _mark_browser_dead()
            return None
        finally:
            _concurrent_users -= 1


async def maybe_cleanup_idle() -> None:
    """Close the browser if idle for _idle_timeout_s. Call from a periodic task."""
    global _browser, _browser_obj, _last_used
    async with _lock:
        if _browser is not None and time.time() - _last_used > _idle_timeout_s and _concurrent_users == 0:
            logger.info("camoufox: idle timeout, closing browser")
            await _close_browser()


async def pool_stats() -> dict:
    """Diagnostic info — call from /sources/health or analytics."""
    return {
        "launches_total": _total_launches,
        "concurrent_users": _concurrent_users,
        "has_browser": _browser is not None,
        "last_used_age_s": int(time.time() - _last_used) if _last_used else None,
    }


async def _ensure_browser() -> None:
    """Lazy-start the shared browser. Idempotent."""
    global _browser, _browser_obj, _total_launches

    # If we already have a browser ref and it has pages working, assume OK.
    # NOTE: Playwright's `is_connected()` is unreliable — we instead check
    # whether a quick noop succeeds. Simpler: assume alive if not None and
    # let errors during page use trigger _mark_browser_dead().
    if _browser_obj is not None:
        return

    async with _lock:
        if _browser_obj is not None:
            return

        from camoufox import AsyncCamoufox
        logger.info("camoufox: launching browser (~5-10s, persisted as singleton)")
        _browser = AsyncCamoufox(
            headless=True,
            humanize=True,
            geoip=True,
            locale="en-US",
        )
        await _browser.__aenter__()
        # AsyncCamoufox exposes .browser after start (the underlying Playwright Browser)
        _browser_obj = getattr(_browser, "browser", None) or await _browser.start()
        _total_launches += 1
        logger.info(f"camoufox: browser launched (total launches: {_total_launches})")


async def _close_browser() -> None:
    """Close the browser. Caller must hold _lock or accept that another
    request may grab it mid-close (browser.is_connected() will catch this)."""
    global _browser, _browser_obj
    if _browser is not None:
        try:
            await _browser.__aexit__(None, None, None)
        except Exception:
            pass
    _browser = None
    _browser_obj = None


async def _mark_browser_dead() -> None:
    """Force-close browser so next call gets a fresh one."""
    global _browser_obj
    # Just null the reference so next _ensure_browser() relaunches.
    # Actual close happens in __aexit__, but we don't need to await it —
    # the next acquire() will create a new one above the old.
    _browser_obj = None


def _is_browser_alive(b: Any) -> bool:
    """Best-effort check on a Playwright Browser object."""
    if b is None:
        return False
    return bool(getattr(b, "is_connected", lambda: False)())
