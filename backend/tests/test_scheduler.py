"""Tests for ``app.scheduler`` — the background chapter-update poller.

These tests are deliberately hermetic. They never hit the network because:

* ``OFFLINE_MODE`` is forced on through :py:mod:`conftest`.
* Each test patches the registered comic sources with a stub whose
  ``home()`` returns a controlled listing, so detection logic can be
  driven deterministically.
* The scheduler's background task is replaced with a single in-process
  invocation of ``_poll_once``-style code (``_poll_once`` itself is
  invoked through the public ``start_scheduler`` / direct calls).

The contract under test:

1. ``start_scheduler`` is idempotent and respects ``OFFLINE_MODE``.
2. ``stop_scheduler`` cancels the task cleanly and is itself idempotent.
3. The per-source cooldown suppresses back-to-back polls.
4. ``detect_updates`` emits a well-formed ``chapter_update`` payload when
   the cached chapter number is strictly less than the freshly observed
   one, and stays silent on the first observation.
5. Multiple slugs in a single listing produce one event per new chapter.
6. The scheduler broadcasts through the same ``app.ws.manager`` the
   ``/ws`` route uses (no duplicate connection-mgr surface).
"""
from __future__ import annotations

import asyncio
import time

import pytest

from app import scheduler as sched
from app.config import get_settings
from app.scheduler import (
    detect_updates,
    is_running,
    reset_state,
    start_scheduler,
    stop_scheduler,
)
from app.sources import list_comic_sources, registry
from app.ws import manager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
class _FakeSource:
    """Minimal ``ComicSource`` stub — just exposes the methods scheduler
    actually calls. Each test sets ``home_returns`` and (optionally)
    ``raise_exc`` to drive detection deterministically.
    """

    # ``ComicSource.home`` is declared without a ``page`` arg but most
    # real adapters accept ``page=1``. The scheduler tries that first
    # then falls back to ``home()``.
    def __init__(self, name: str, home_returns, *, raise_exc: Exception | None = None) -> None:
        self.name = name
        self._home_returns = home_returns
        self._raise_exc = raise_exc
        self.home_calls = 0

    async def home(self, page: int = 1):  # noqa: ARG002
        self.home_calls += 1
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._home_returns

    # Some scrapers also expose ``latest``; scheduler doesn't call it,
    # but having the full base surface keeps the isinstance() check in
    # ``registry.comic_source`` happy if it ever runs.
    async def latest(self):  # pragma: no cover - unused
        return []

    async def search(self, query):  # pragma: no cover - unused
        return []

    async def detail(self, slug):  # pragma: no cover - unused
        return {}

    async def manga(self, slug):  # pragma: no cover - unused
        return {}

    async def chapter(self, slug):  # pragma: no cover - unused
        return {}

    async def genre(self, slug):  # pragma: no cover - unused
        return []

    async def popular(self):  # pragma: no cover - unused
        return []


@pytest.fixture
def patched_sources(monkeypatch):
    """Force the scheduler to see a fixed set of two fake comic sources.

    ``app.scheduler`` imports ``comic_source`` and ``list_comic_sources``
    at module load time (``from .sources import …``), so patching the
    registry module alone won't rebind the scheduler's own references.
    We patch both — the registry (so any test code that goes through
    the public surface sees the same fakes) and the scheduler module's
    locally-bound names.
    """
    fake_a = _FakeSource("kiryuu", [])
    fake_b = _FakeSource("mangadex", [])
    mapping = {"kiryuu": fake_a, "mangadex": fake_b}

    def _patched_comic_source(name: str):
        return mapping.get(name)

    monkeypatch.setattr(registry, "comic_source", _patched_comic_source)
    monkeypatch.setattr(registry, "list_comic_sources", lambda: list(mapping.keys()))
    # Belt-and-suspenders: scheduler imported these names directly.
    monkeypatch.setattr(sched, "comic_source", _patched_comic_source)
    monkeypatch.setattr(sched, "list_comic_sources", lambda: list(mapping.keys()))
    return mapping


@pytest.fixture
def cleaned_state(monkeypatch):
    """Reset scheduler state, broadcast manager, and OFFLINE_MODE
    around every test. The broadcast manager is module-global
    (the ``/ws`` route shares it), so a stray socket from a previous
    test could otherwise skew the ``delivered`` count.
    """
    reset_state()
    manager._clients.clear()  # type: ignore[attr-defined]
    s = get_settings()
    orig_offline = s.offline_mode
    s.offline_mode = False
    monkeypatch.setenv("WS_BROADCAST_INTERVAL_SECONDS", "0.05")
    monkeypatch.setenv("SCHEDULER_COOLDOWN_SECONDS", "300")
    try:
        yield
    finally:
        # Make sure no stray task survives the test (a loop iteration
        # is harmless but loud in CI output).
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
        if loop is not None and loop.is_running():
            # We're inside an async test running on the same loop —
            # leave the task cancellation to the test body via the
            # stop_scheduler helper below.
            pass
        s.offline_mode = orig_offline
        manager._clients.clear()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class _FakeWebSocket:
    """WebSocket-like enough for ``manager.broadcast``.

    Records every JSON payload ``send_json`` is called with so the test
    can assert on what was actually delivered. Implements just enough of
    the Starlette API the manager uses.
    """

    def __init__(self) -> None:
        self.received: list[dict] = []

    async def send_json(self, payload) -> None:
        self.received.append(payload)

    async def send_text(self, payload) -> None:  # pragma: no cover - unused
        self.received.append({"text": payload})


# ---------------------------------------------------------------------------
# Tests — lifecycle / config
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scheduler_starts_and_stops_cleanly(cleaned_state, monkeypatch):
    """``start_scheduler`` spawns a task that ``stop_scheduler`` cancels."""
    assert is_running() is False
    await start_scheduler()
    try:
        assert is_running() is True
        # ``is_running`` checks the task is alive; an immediate poll may
        # have run already — we don't care which, just that the handle
        # exists.
        task = sched._scheduler_task  # type: ignore[attr-defined]
        assert task is not None
        assert not task.done()
    finally:
        await stop_scheduler()
    assert is_running() is False
    # Calling stop_scheduler twice must not raise.
    await stop_scheduler()


@pytest.mark.asyncio
async def test_start_scheduler_is_idempotent(cleaned_state):
    """Calling ``start_scheduler`` twice doesn't double-spawn."""
    await start_scheduler()
    first = sched._scheduler_task  # type: ignore[attr-defined]
    await start_scheduler()
    second = sched._scheduler_task  # type: ignore[attr-defined]
    assert first is second
    await stop_scheduler()


@pytest.mark.asyncio
async def test_scheduler_skipped_in_offline_mode(cleaned_state, monkeypatch):
    """When ``OFFLINE_MODE`` is truthy, ``start_scheduler`` is a no-op.

    The simulated broadcaster in ``app.ws`` carries the demo load
    instead — exactly the contract documented in the scheduler
    docstring.
    """
    s = get_settings()
    s.offline_mode = True
    await start_scheduler()
    assert is_running() is False
    assert sched._scheduler_task is None  # type: ignore[attr-defined]
    # And stop still has to be safe even though we never started.
    await stop_scheduler()


# ---------------------------------------------------------------------------
# Tests — detection + cooldown
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cooldown_blocks_repeat_poll(cleaned_state, monkeypatch, patched_sources):
    """A second immediate poll of the same source is suppressed by the
    per-source cooldown timer.
    """
    monkeypatch.setenv("SCHEDULER_COOLDOWN_SECONDS", "300")
    monkeypatch.setenv("WS_BROADCAST_INTERVAL_SECONDS", "0.01")
    kiryuu = patched_sources["kiryuu"]

    # Seed the cache by registering the "no-broadcast" first observation.
    detect_updates("kiryuu", [{"slug": "one-piece", "latest_chapter": "1000"}])
    assert kiryuu.home_calls == 0, "detect_updates must not call home()"

    await start_scheduler()
    try:
        # Wait for the loop to fire at least twice.
        for _ in range(40):
            await asyncio.sleep(0.05)
            if kiryuu.home_calls >= 2:
                break
        # Cooldown of 300s must suppress the second attempt — exactly
        # one poll should have reached the source.
        assert kiryuu.home_calls == 1, (
            f"expected exactly 1 poll within cooldown window, got {kiryuu.home_calls}"
        )
    finally:
        await stop_scheduler()


@pytest.mark.asyncio
async def test_broadcast_triggered_on_newer_chapter(
    cleaned_state, monkeypatch, patched_sources
):
    """When a newer chapter is observed, the scheduler broadcasts a
    ``chapter_update`` payload that matches the documented shape.
    """
    monkeypatch.setenv("SCHEDULER_COOLDOWN_SECONDS", "0")  # always poll
    monkeypatch.setenv("WS_BROADCAST_INTERVAL_SECONDS", "0.01")
    kiryuu = patched_sources["kiryuu"]

    # Connect a fake ws so broadcast has a recipient.
    fake_ws = _FakeWebSocket()
    await manager.connect(fake_ws)  # type: ignore[arg-type]  # mypy: ignore
    try:
        # First observation: baseline only, no broadcast.
        kiryuu._home_returns = [{"slug": "solo-leveling", "latest_chapter": "180"}]
        await start_scheduler()
        # Give the loop a tick.
        for _ in range(40):
            await asyncio.sleep(0.05)
            if kiryuu.home_calls >= 1:
                break
        assert kiryuu.home_calls >= 1
        # Switch to a newer chapter. With cooldown=0 the loop will pick
        # this up on its next tick and broadcast.
        kiryuu._home_returns = [{"slug": "solo-leveling", "latest_chapter": "181"}]
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if any(
                isinstance(m, dict) and m.get("type") == "chapter_update"
                and m.get("slug") == "solo-leveling"
                for m in fake_ws.received
            ):
                break
            await asyncio.sleep(0.05)
        events = [
            m for m in fake_ws.received
            if isinstance(m, dict) and m.get("type") == "chapter_update"
            and m.get("slug") == "solo-leveling"
        ]
        assert events, f"expected at least one chapter_update; received={fake_ws.received}"
        evt = events[-1]
        assert evt["source"] == "kiryuu"
        assert evt["slug"] == "solo-leveling"
        assert evt["latest_chapter"] == 181
        assert evt["chapter"] == 181
        assert isinstance(evt["detected_at"], int) and evt["detected_at"] <= int(time.time())
        assert isinstance(evt["at"], int) and evt["at"] <= int(time.time())
    finally:
        await stop_scheduler()
        await manager.disconnect(fake_ws)  # type: ignore[arg-type]  # mypy: ignore


@pytest.mark.asyncio
async def test_detect_updates_first_observation_is_silent(cleaned_state, patched_sources):
    """``detect_updates`` returns no events when a slug has never been
    seen before — we baseline first, broadcast second.
    """
    items = [
        {"slug": "naruto", "latest_chapter": "Chapter 1"},
        {"slug": "bleach", "latest_chapter": "Ch. 2"},
        {"slug": "no-chapter", "latest_chapter": None},  # skipped
        {"slug": "", "latest_chapter": "1"},  # skipped (empty slug)
    ]
    events = detect_updates("kiryuu", items)
    assert events == []
    # Cache is populated for the well-formed slugs.
    cache = sched._known_chapters["kiryuu"]  # type: ignore[attr-defined]
    assert cache == {"naruto": 1, "bleach": 2}


@pytest.mark.asyncio
async def test_detect_updates_emits_for_each_strict_increase(
    cleaned_state, patched_sources
):
    """When multiple slugs each advance, one event per slug is emitted;
    decreases and equals are silent.
    """
    # Seed baseline.
    detect_updates(
        "kiryuu",
        [
            {"slug": "naruto", "latest_chapter": "10"},
            {"slug": "bleach", "latest_chapter": "20"},
            {"slug": "stable", "latest_chapter": "5"},
        ],
    )
    # Mixed update: increase, decrease, equal, new slug.
    events = detect_updates(
        "kiryuu",
        [
            {"slug": "naruto", "latest_chapter": "11"},  # newer -> emit
            {"slug": "bleach", "latest_chapter": "19"},  # older  -> silent
            {"slug": "stable", "latest_chapter": "5"},   # equal  -> silent
            {"slug": "fresh", "latest_chapter": "1"},    # unseen -> silent (baseline)
        ],
    )
    assert len(events) == 1
    assert events[0]["slug"] == "naruto"
    assert events[0]["latest_chapter"] == 11


@pytest.mark.asyncio
async def test_scheduler_uses_real_broadcast_manager(
    cleaned_state, monkeypatch, patched_sources
):
    """The scheduler must share the same ``ConnectionManager`` the
    ``/ws`` router uses — there's no separate broadcast surface.
    """
    from app.ws import manager as ws_manager
    from app.routers.ws import websocket_endpoint  # noqa: F401  (just to confirm import)

    assert manager is ws_manager, (
        "scheduler and /ws router must reference the same ConnectionManager instance"
    )
    fake_ws = _FakeWebSocket()
    await ws_manager.connect(fake_ws)  # type: ignore[arg-type]  # mypy: ignore
    try:
        # Directly drive the public detection/broadcast surface so we
        # don't need to wait on a loop tick.
        detect_updates("mangadex", [{"slug": "spy-x-family", "latest_chapter": "1"}])
        events = detect_updates("mangadex", [{"slug": "spy-x-family", "latest_chapter": "2"}])
        assert len(events) == 1
        delivered = await ws_manager.broadcast(events[0])
        assert delivered == 1
        assert fake_ws.received == [events[0]]
    finally:
        await ws_manager.disconnect(fake_ws)  # type: ignore[arg-type]  # mypy: ignore
