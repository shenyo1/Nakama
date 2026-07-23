"""WebSocket routes: /ws (real-time update stream) and /admin/broadcast.

* ``GET /ws`` — accept a WebSocket connection and stream simulated chapter
  updates. Authentication is opt-in: when ``API_KEY`` is set, the client
  must present it as a ``?token=<key>`` query parameter. When the key is
  unset (the default for local/offline use), the endpoint is open.

* ``POST /admin/broadcast`` — manually push a single event payload to every
  connected WebSocket client. The ``event`` body is forwarded verbatim, so
  the format matches what the periodic broadcaster emits (``type``,
  ``source``, ``slug``, ``chapter``, ``at`` …). When ``API_KEY`` is set
  the caller must supply ``X-API-Key`` matching the configured key.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..config import get_settings
from ..sources import (
    list_anime_sources,
    list_comic_sources,
    list_novel_sources,
)
from ..ws import make_hello_payload, manager


router = APIRouter(tags=["ws"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _authorized(token: Optional[str]) -> bool:
    """Return True if the request is allowed at the WS layer.

    Open access when API_KEY is unset (local/dev/offline); else require the
    caller-supplied ``token`` query param to match exactly.
    """
    expected = get_settings().api_key
    if not expected:
        return True
    return bool(token) and token == expected


def _all_sources() -> list[str]:
    """Union of every registered source — used for the hello payload."""
    return (
        list(list_anime_sources())
        + list(list_comic_sources())
        + list(list_novel_sources())
    )


# ---------------------------------------------------------------------------
# /ws — live update stream
# ---------------------------------------------------------------------------
@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(
        default=None,
        description="API key (matches Settings.api_key) when auth is enabled.",
    ),
) -> None:
    """Accept a WebSocket and stream ``chapter_update`` events to it.

    On connect:
      1. If ``Settings.api_key`` is set and ``token`` does not match, close
         the socket with code ``1008`` (policy violation) — no welcome.
      2. Otherwise accept, register with the manager, and send a ``hello``
         frame so the client knows which sources are live.

    After that, the connection is held open; the client may send messages
    (we ignore their contents — this endpoint is one-way) until they close.
    The periodic broadcaster (started in ``main.lifespan``) will fan-out
    events to this and every other live client.
    """
    await websocket.accept()

    if not _authorized(token):
        # 1008 = policy violation. We accepted first so we can send a
        # structured error message; the close frame tells the client why.
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "unauthorized",
                    "detail": "Invalid or missing token for /ws.",
                }
            )
        finally:
            await websocket.close(code=1008)
        return

    await manager.connect(websocket)
    try:
        await websocket.send_json(make_hello_payload(_all_sources()))
        # Keep the socket alive. We don't process inbound frames — this is a
        # pure server-push channel. Any send by the client is silently
        # discarded (a receive is required to detect client-side close).
        while True:
            # ``receive_text`` returns None on close; raising WebSocketDisconnect
            # is the canonical exit signal.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        # Anything else: log + drop quietly so a misbehaving client doesn't
        # take down the connection for everyone else.
        pass
    finally:
        await manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# /admin/broadcast — manually push a single event to every client
# ---------------------------------------------------------------------------
class BroadcastBody(BaseModel):
    """Body schema for ``POST /admin/broadcast``.

    ``event`` is forwarded verbatim to every connected WebSocket. We don't
    enforce a schema on ``event`` because the broadcaster's own payloads
    (chapter_update, hello, ping, …) may evolve. A ``type`` field is
    recommended but not required.
    """

    event: dict[str, Any] = Field(
        ...,
        description="JSON object to forward to every connected WebSocket.",
        examples=[
            {
                "type": "chapter_update",
                "source": "kiryuu",
                "slug": "solo-leveling",
                "chapter": 181,
            }
        ],
    )


@router.post(
    "/admin/broadcast",
    summary="Manually broadcast a JSON event to every connected /ws client",
)
async def admin_broadcast(
    payload: BroadcastBody,
    request: Request,
) -> dict[str, Any]:
    """Forward ``payload.event`` to every connected WebSocket.

    When ``API_KEY`` is configured, the caller must send the matching
    ``X-API-Key`` header. The HTTP-level auth middleware in ``main.py``
    already exempts non-/anime/comic/novel paths, so the admin endpoint
    is unrestricted by that middleware; we enforce the API key here
    explicitly so the gate still works.
    """
    settings = get_settings()
    if settings.api_key:
        provided = request.headers.get("X-API-Key", "")
        if provided != settings.api_key:
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid X-API-Key header.",
            )

    delivered = await manager.broadcast(payload.event)
    return {
        "ok": True,
        "delivered": delivered,
        "clients": manager.client_count,
        "event": payload.event,
    }
