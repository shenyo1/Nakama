"""Background poller that detects new chapters from registered comic sources
and broadcasts ``chapter_update`` events to all connected ``/ws`` clients.

The scheduler is intentionally minimal and decoupled from the rest of the app:

* A single ``asyncio`` task runs the loop. ``start_scheduler`` spawns it;
  ``stop_scheduler`` cancels and awaits it. Both are idempotent and safe to
  call from the FastAPI lifespan handler.

* Each iteration calls :py:meth:`ComicSource.home` (page 1) on every source
  in :py:func:`app.sources.list_comic_sources` and compares the result
  against an in-memory cache keyed by ``(source, slug)``. When the latest
  chapter number increases, an event is broadcast via
  :py:attr:`app.ws.manager.broadcast`.

* An in-memory "last-polled" map keyed by source name enforces a per-source
  cooldown (default 5 minutes) so the loop never hits the same upstream
  more often than the configured ``WS_BROADCAST_INTERVAL_SECONDS`` × N
  thresholds — even if the source list changes mid-run.

* When ``OFFLINE_MODE=1`` is set, the loop short-circuits and emits no
  network or broadcast traffic; the existing simulated broadcaster in
  :py:mod:`app.ws` continues to drive the demo experience.

Configuration is read from environment variables at start time:

* ``WS_BROADCAST_INTERVAL_SECONDS`` — loop period. Default ``60``.
* ``SCHEDULER_COOLDOWN_SECONDS`` — per-source minimum gap between
  successful polls. Default ``300`` (5 minutes).
* ``OFFLINE_MODE`` — when truthy, the scheduler is a no-op
  (``start_scheduler`` returns immediately and ``stop_scheduler`` is safe).

The cache and cooldown state live in module-level dicts so tests can reset
them by reimporting the module or by clearing them directly.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any, Optional

from .config import get_settings
from .sources import comic_source, list_comic_sources
from .ws import manager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def _env_float(name: str, default: float) -> float:
    """Read a float from the environment with a fallback default.

    A bad value falls back to the default rather than raising — start-up
    should always succeed even if the operator mistypes the env var.
    """
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


# Cadence: how often the loop wakes up and considers polling each source.
# Default 60s — the task says "every 60s".
_DEFAULT_INTERVAL_SECONDS = 60.0

# Cooldown: minimum gap between two consecutive *successful* polls of the
# same source. Default 5 minutes — well below the WS cadence so the loop
# doesn't get into a tight retry loop on a flaky upstream.
_DEFAULT_COOLDOWN_SECONDS = 300.0


def _interval_seconds() -> float:
    return max(0.05, _env_float("WS_BROADCAST_INTERVAL_SECONDS", _DEFAULT_INTERVAL_SECONDS))


def _cooldown_seconds() -> float:
    return max(0.0, _env_float("SCHEDULER_COOLDOWN_SECONDS", _DEFAULT_COOLDOWN_SECONDS))


# ---------------------------------------------------------------------------
# State — module-level so tests can introspect/reset.
# ---------------------------------------------------------------------------
# Latest known chapter number per ``(source, slug)``. ``None`` (missing)
# means we've never seen that slug before — the first observation is
# treated as "no broadcast" so we don't spam clients at boot.
_known_chapters: dict[str, dict[str, float]] = {}

# Wall-clock time of the last *attempted* poll per source. Used to enforce
# the per-source cooldown independently of the loop interval. When a poll
# fails we still update this so a misbehaving upstream can't make us
# hammer it.
_last_polled_at: dict[str, float] = {}

# Task handle for the running loop. ``None`` when the scheduler is
# stopped; the start function is idempotent on a live handle.
_scheduler_task: Optional[asyncio.Task] = None

# Snapshot of the interval actually used at start time. Tests assert
# this to confirm the env var was honoured.
_started_interval: Optional[float] = None


def reset_state() -> None:
    """Clear the in-memory cache and cooldowns.

    Intended for tests. Production code never needs this — the state
    lives only inside this process and is naturally discarded on
    shutdown.
    """
    global _scheduler_task, _started_interval  # noqa: PLW0603
    _known_chapters.clear()
    _last_polled_at.clear()
    _scheduler_task = None
    _started_interval = None


# ---------------------------------------------------------------------------
# Helpers — chapter-number extraction
# ---------------------------------------------------------------------------
# Match strings like "Chapter 181", "Ch. 181.5", "181", "Vol. 3 Ch. 12".
# We deliberately accept the integer-only form so sources that just
# print "181" work without modification.
_CHAPTER_RX = re.compile(r"(\d+(?:\.\d+)?)")


def _parse_chapter_number(value: Any) -> Optional[float]:
    """Best-effort: turn ``ComicSummary.latest_chapter`` into a float.

    Returns ``None`` when the value isn't a string we can scrape a number
    from. We use ``float`` (not ``int``) so a sticky source that emits
    "181.5" doesn't get mistaken for "181".
    """
    if value is None:
        return None
    text = str(value)
    m = _CHAPTER_RX.search(text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _extract_listing(items: list[dict]) -> dict[str, float]:
    """Reduce a ``home()`` listing to ``{slug: chapter_number}``.

    Entries missing a slug or with an unparseable chapter number are
    dropped silently — they don't break the cache, they just don't
    contribute to detection.
    """
    out: dict[str, float] = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        slug = item.get("slug") or item.get("id")
        if not slug or not isinstance(slug, str):
            continue
        chap = _parse_chapter_number(item.get("latest_chapter"))
        if chap is None:
            continue
        out[slug] = chap
    return out


# ---------------------------------------------------------------------------
# Detectors — exported so tests can call them without spinning the loop
# ---------------------------------------------------------------------------
def detect_updates(source_name: str, items: list[dict]) -> list[dict[str, Any]]:
    """Compare a fresh listing against the in-memory cache.

    Returns a list of payload dicts, one per detected new chapter. Each
    payload matches the WebSocket chapter_update shape::

        {
            "type": "chapter_update",
            "source": <source_name>,
            "slug":   <slug>,
            "latest_chapter": <int>,
            "chapter": <int>,            # alias for backwards compatibility
            "detected_at": <unix ts int>,
            "at": <unix ts int>,          # alias matching simulated broadcaster
        }

    The first observation of a slug never produces an event — we only
    emit when the cached chapter number is *strictly less than* the new
    one. The cache is updated regardless so the next call sees the
    up-to-date baseline.
    """
    new_listing = _extract_listing(items)
    cached: dict[str, float] = _known_chapters.get(source_name, {})
    now = int(time.time())
    payloads: list[dict[str, Any]] = []
    next_cache: dict[str, float] = {}

    def _coerce(value: float) -> float | int:
        # Store as int when we can — keeping floats would force every
        # caller to handle two numeric types. ``int()`` truncates ties
        # like 181.5 to 181 which is fine for "newer?" detection.
        return int(value) if value == int(value) else value

    for slug, chap in new_listing.items():
        chap_int: float = _coerce(chap)
        prev = cached.get(slug)
        if prev is None:
            # First observation — baseline only.
            next_cache[slug] = chap_int
            continue
        try:
            is_newer = float(chap) > float(prev)
        except (TypeError, ValueError):
            is_newer = False
        if is_newer:
            payloads.append(
                {
                    "type": "chapter_update",
                    "source": source_name,
                    "slug": slug,
                    "latest_chapter": _coerce(chap),
                    "chapter": _coerce(chap),
                    "detected_at": now,
                    "at": now,
                }
            )
        next_cache[slug] = chap_int
    # Also remember slugs we've seen before but didn't see this round —
    # so we don't fire stale "newer" events when they reappear.
    for slug, chap in cached.items():
        if slug not in next_cache:
            next_cache[slug] = chap
    _known_chapters[source_name] = next_cache
    return payloads


def _cooldown_active(source_name: str, cooldown: float) -> bool:
    """True when the source was polled within ``cooldown`` seconds."""
    if cooldown <= 0:
        return False
    last = _last_polled_at.get(source_name)
    if last is None:
        return False
    return (time.monotonic() - last) < cooldown


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------
async def _poll_once(interval: float, cooldown: float) -> int:
    """Run one pass over every registered comic source.

    Each source is polled only when its cooldown has elapsed. Returns the
    number of broadcasts emitted during the pass — handy for tests and
    for diagnostic logging.
    """
    emitted = 0
    for source_name in list_comic_sources():
        if _cooldown_active(source_name, cooldown):
            # Skip silently — there's no useful signal we'd add.
            continue
        source = comic_source(source_name)
        if source is None:
            continue
        try:
            # ``home`` takes an optional ``page`` arg in most adapters; we
            # only ever want page 1 for polling. We try the signature
            # ``home(page=1)`` explicitly, falling back to ``home()`` so
            # an adapter that hasn't been updated still works.
            home = getattr(source, "home")
            try:
                items = await home(page=1)  # type: ignore[call-arg]
            except TypeError:
                items = await home()
        except Exception as exc:  # noqa: BLE001
            logger.warning("scheduler: %s poll failed: %s", source_name, exc)
            # Update cooldown even on failure so we don't tight-loop.
            _last_polled_at[source_name] = time.monotonic()
            continue
        # Successful fetch — record and look for updates.
        _last_polled_at[source_name] = time.monotonic()
        for payload in detect_updates(source_name, items or []):
            await manager.broadcast(payload)
            emitted += 1
    return emitted


async def _scheduler_loop(interval: float, cooldown: float) -> None:
    """Forever: sleep, poll, repeat. Exceptions are logged, never fatal."""
    while True:
        try:
            await asyncio.sleep(interval)
            await _poll_once(interval, cooldown)
        except asyncio.CancelledError:
            # Normal shutdown — let the task die quietly.
            raise
        except Exception as exc:  # noqa: BLE001
            # Defensive: never let the loop exit on an unexpected error.
            logger.exception("scheduler iteration failed: %s", exc)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
def is_running() -> bool:
    """True when the background task is alive and not yet cancelled."""
    return _scheduler_task is not None and not _scheduler_task.done()


async def start_scheduler() -> None:
    """Start the background poller. Idempotent and OFFLINE-aware.

    When ``OFFLINE_MODE`` is set, this is a no-op: the simulated
    broadcaster in :py:mod:`app.ws` drives the demo. The scheduler
    still exposes ``is_running()`` as False so callers can short-circuit
    cleanly.
    """
    global _scheduler_task, _started_interval
    if get_settings().offline_mode:
        logger.info("scheduler: OFFLINE_MODE set, skipping start")
        return
    if is_running():
        return
    interval = _interval_seconds()
    cooldown = _cooldown_seconds()
    _started_interval = interval
    _scheduler_task = asyncio.create_task(
        _scheduler_loop(interval, cooldown),
        name="chapter-poll-scheduler",
    )
    logger.info(
        "scheduler: started (interval=%.1fs, cooldown=%.1fs)",
        interval,
        cooldown,
    )


async def stop_scheduler() -> None:
    """Cancel the background poller and await it. Idempotent."""
    global _scheduler_task
    task = _scheduler_task
    if task is None:
        return
    _scheduler_task = None
    if not task.done():
        task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):  # noqa: BLE001
        # The loop already logs unexpected exceptions. On the
        # cancel path we just want a clean re-join.
        pass
    logger.info("scheduler: stopped")


__all__ = [
    "start_scheduler",
    "stop_scheduler",
    "is_running",
    "detect_updates",
    "reset_state",
    "_parse_chapter_number",
    "_extract_listing",
]
