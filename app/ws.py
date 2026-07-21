"""WebSocket connection manager + simulated chapter-update broadcaster.

The ``ConnectionManager`` owns the set of active WebSocket sessions, handles
connect/disconnect bookkeeping, and fans-out broadcast events. It is process-
local: each uvicorn worker has its own manager and its own set of clients.

A background ``asyncio`` task (started/stopped via :func:`start_broadcaster`
and :func:`stop_broadcaster`) emits a simulated ``chapter_update`` event every
``WS_BROADCAST_INTERVAL_SECONDS`` seconds (default 30). Right now the events
are randomly sampled from a fixed pool of (source, slug) pairs. The intent is
to swap this generator for a real one that observes the source scrapers
once that hook is in place.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any, Iterable, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Simulated-event pool
# ---------------------------------------------------------------------------
# These pairs drive the periodic ``chapter_update`` messages broadcast while
# the real scraper-event integration is still TODO. Keep the list small and
# representative of what real scrapers would emit.
_SIMULATED_EVENTS: list[tuple[str, str]] = [
    ("kiryuu", "solo-leveling"),
    ("kiryuu", "one-piece"),
    ("kiryuu", "boruto"),
    ("komiku", "one-piece"),
    ("komiku", "naruto"),
    ("komikcast", "chainsaw-man"),
    ("mangadex", "spy-x-family"),
    ("shinigami", "tensei-shitara"),
    ("sakuranovel", "the-beginning-after-the-end"),
    ("otakudesu", "boruto"),
]


# ---------------------------------------------------------------------------
# ConnectionManager
# ---------------------------------------------------------------------------
class ConnectionManager:
    """In-process registry of active WebSocket connections.

    The Starlette/FastAPI WebSocket route hands the socket off to
    ``connect``; ``broadcast`` pushes a JSON-serialisable payload to every
    connected client; ``disconnect`` removes dead clients. All public methods
    are coroutine-safe: a single ``asyncio.Lock`` guards mutations of
    ``_clients`` so a send-failure during broadcast cannot race with a
    concurrent disconnect.
    """

    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    @property
    def client_count(self) -> int:
        """Number of currently registered clients (for diagnostics/tests)."""
        return len(self._clients)

    async def connect(self, ws: WebSocket) -> None:
        """Register a freshly accepted WebSocket.

        The caller is expected to have already called ``await ws.accept()``
        before invoking this — we don't double-accept because Starlette would
        raise. We do, however, register the socket under the lock so a
        concurrent broadcast can't miss us.
        """
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket from the registry. Idempotent."""
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, payload: dict[str, Any]) -> int:
        """Send ``payload`` (already a JSON-serialisable dict) to every client.

        Returns the number of clients successfully delivered to. Dead clients
        are evicted silently so a single misbehaving subscriber can't poison
        the broadcast.
        """
        # Take a snapshot under the lock so the send loop runs lock-free and
        # so a slow client can't block new connect() calls.
        async with self._lock:
            recipients: list[WebSocket] = list(self._clients)
        if not recipients:
            return 0

        delivered = 0
        dead: list[WebSocket] = []
        for ws in recipients:
            try:
                await ws.send_json(payload)
                delivered += 1
            except Exception as exc:
                # Anything from RuntimeError (already disconnected) to
                # ConnectionClosed counts as a dead client. Drop silently.
                logger.debug("ws broadcast drop: %s", exc)
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)
        return delivered


# Module-level singleton — FastAPI app routes share this instance.
manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Background broadcaster
# ---------------------------------------------------------------------------
_BROADCAST_TASK: Optional[asyncio.Task] = None

# Default cadence: 30s. Tests can lower this by setting
# WS_BROADCAST_INTERVAL_SECONDS before the lifespan starts the task.
import os as _os  # local alias keeps the public surface tidy


def _broadcast_interval() -> float:
    try:
        return max(0.05, float(_os.getenv("WS_BROADCAST_INTERVAL_SECONDS", "30")))
    except ValueError:
        return 30.0


async def _broadcaster_loop(interval: float) -> None:
    """Periodically generate a simulated chapter_update and broadcast it.

    The loop sleeps ``interval`` seconds between iterations; an unexpected
    exception is logged but does not kill the task — we'd rather emit nothing
    for a while than break the connection manager.
    """
    while True:
        try:
            await asyncio.sleep(interval)
            if manager.client_count == 0:
                # Nothing to do — skip the dict allocation.
                continue
            payload = make_simulated_chapter_update()
            await manager.broadcast(payload)
        except asyncio.CancelledError:
            # Normal shutdown path — let the task die.
            raise
        except Exception as exc:  # pragma: no cover — defensive
            logger.exception("ws broadcaster iteration failed: %s", exc)


def make_simulated_chapter_update() -> dict[str, Any]:
    """Build one random ``chapter_update`` event.

    The shape mirrors what a future real scraper hook will emit:

        {"type": "chapter_update", "source": str, "slug": str,
         "chapter": int, "at": int}

    Exposed as a free function so tests can deterministically assert shape
    without patching internal state.
    """
    source, slug = random.choice(_SIMULATED_EVENTS)
    return {
        "type": "chapter_update",
        "source": source,
        "slug": slug,
        "chapter": random.randint(1, 300),
        "at": int(time.time()),
    }


def make_hello_payload(sources: Iterable[str]) -> dict[str, Any]:
    """Build the welcome message sent right after accept()."""
    return {
        "type": "hello",
        "connected_at": int(time.time()),
        "sources": list(sources),
    }


async def start_broadcaster() -> None:
    """Start the background broadcaster task (idempotent)."""
    global _BROADCAST_TASK
    if _BROADCAST_TASK is not None and not _BROADCAST_TASK.done():
        return
    _BROADCAST_TASK = asyncio.create_task(
        _broadcaster_loop(_broadcast_interval()),
        name="ws-broadcaster",
    )


async def stop_broadcaster() -> None:
    """Cancel the broadcaster task and await it. Safe to call repeatedly."""
    global _BROADCAST_TASK
    task = _BROADCAST_TASK
    if task is None:
        return
    _BROADCAST_TASK = None
    if not task.done():
        task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):  # noqa: BLE001
        # Any exception here is already recorded/logged in the loop. We just
        # want the task to be cleanly reaped on shutdown.
        pass
