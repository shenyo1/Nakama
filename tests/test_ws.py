"""Tests for the /ws WebSocket endpoint and /admin/broadcast HTTP endpoint.

The router defines two entry points:

  * ``GET /ws`` — accepts a WebSocket, sends a ``hello`` frame, and streams
    ``chapter_update`` events to the client. The connection-manager
    (``app.ws.manager``) is module-global, so each test must drain the set
    before and after so a stray client from a prior test does not skew the
    count.

  * ``POST /admin/broadcast`` — manually pushes one event to every
    connected client.

We use ``starlette.testclient.TestClient`` because it offers the blocking
``websocket_connect()`` context-manager that's the simplest way to drive a
Starlette WebSocket route from a unittest. The same ``app`` ASGI instance
from ``conftest.py`` is reused.
"""
from __future__ import annotations

import json
import time

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.config import get_settings
from app.main import app
from app.sources import list_anime_sources, list_comic_sources, list_novel_sources
from app.ws import manager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def ws_client():
    """Synchronous Starlette TestClient for WebSocket testing.

    Each call yields a fresh client built around the shared ``app`` and
    clears the connection manager before AND after so the broadcast targets
    we count on are exactly the ones we open in the test.
    """
    # Drain any stray connections from a previous test. The manager is
    # module-global; without this reset, a prior test could leak sockets.
    manager._clients.clear()  # type: ignore[attr-defined]

    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        manager._clients.clear()  # type: ignore[attr-defined]


@pytest.fixture
def api_key_enabled():
    """Configure Settings.api_key for the duration of one test."""
    settings = get_settings()
    original = settings.api_key
    settings.api_key = "test-secret-key-123"
    try:
        yield settings.api_key
    finally:
        settings.api_key = original


# ---------------------------------------------------------------------------
# Tests — /ws
# ---------------------------------------------------------------------------
def test_ws_sends_hello_on_connect(ws_client):
    """Connecting to /ws yields a ``hello`` message with the source list."""
    with ws_client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        assert isinstance(hello["connected_at"], int)
        assert hello["connected_at"] <= int(time.time())

        expected_sources = sorted(
            list(list_anime_sources())
            + list(list_comic_sources())
            + list(list_novel_sources())
        )
        assert sorted(hello["sources"]) == expected_sources

        # After the hello, the connection is held open — the manager
        # should report it as registered.
        assert manager.client_count >= 1


def test_ws_rejects_missing_token_when_api_key_enabled(ws_client, api_key_enabled):
    """Without the matching token, /ws closes with code 1008 (policy violation)."""
    with ws_client.websocket_connect("/ws") as ws:
        # Server sends a structured error frame then closes with 1008.
        # We must receive the frame first; otherwise exit just sees the close.
        try:
            err = ws.receive_json()
            assert err.get("type") == "error"
            assert err.get("code") == "unauthorized"
        except WebSocketDisconnect as exc:
            assert exc.code == 1008
            return
        # And then the close should follow.
        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_text()
        assert exc_info.value.code == 1008
    # No connection should have been registered.
    assert manager.client_count == 0


def test_ws_accepts_correct_token_when_api_key_enabled(ws_client, api_key_enabled):
    """With the right token, /ws streams the hello frame."""
    with ws_client.websocket_connect(f"/ws?token={api_key_enabled}") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"


def test_ws_receives_admin_broadcast(ws_client):
    """A live /ws client receives events pushed via /admin/broadcast."""
    with ws_client.websocket_connect("/ws") as ws:
        # Drain the hello frame so receive_json() in the loop sees broadcast
        # frames only.
        ws.receive_json()  # hello

        # Manually push an event over the admin HTTP endpoint. We send the
        # HTTP request *after* opening the WS so the broadcast finds a real
        # recipient registered with the manager.
        payload = {
            "type": "chapter_update",
            "source": "kiryuu",
            "slug": "solo-leveling",
            "chapter": 181,
            "at": int(time.time()),
        }
        r = ws_client.post("/admin/broadcast", json={"event": payload})
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["delivered"] >= 1
        assert body["event"] == payload

        msg = ws.receive_json()
        assert msg == payload


# ---------------------------------------------------------------------------
# Tests — /admin/broadcast
# ---------------------------------------------------------------------------
def test_admin_broadcast_requires_api_key_when_enabled(ws_client, api_key_enabled):
    """When API_KEY is set, /admin/broadcast without X-API-Key is 401."""
    r = ws_client.post(
        "/admin/broadcast",
        json={"event": {"type": "ping"}},
    )
    assert r.status_code == 401


def test_admin_broadcast_with_api_key_passes(ws_client, api_key_enabled):
    """When X-API-Key matches, the broadcast call succeeds (even with no clients)."""
    r = ws_client.post(
        "/admin/broadcast",
        json={"event": {"type": "ping", "ts": 12345}},
        headers={"X-API-Key": api_key_enabled},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["delivered"] == 0
    assert body["clients"] == 0
    assert body["event"]["type"] == "ping"


# ---------------------------------------------------------------------------
# Tests — chapter-update shape
# ---------------------------------------------------------------------------
def test_simulated_chapter_update_shape():
    """``make_simulated_chapter_update`` emits a well-formed chapter_update."""
    from app.ws import make_simulated_chapter_update

    ev = make_simulated_chapter_update()
    assert ev["type"] == "chapter_update"
    assert isinstance(ev["source"], str) and ev["source"]
    assert isinstance(ev["slug"], str) and ev["slug"]
    assert isinstance(ev["chapter"], int) and 1 <= ev["chapter"] <= 300
    assert isinstance(ev["at"], int) and ev["at"] <= int(time.time())
