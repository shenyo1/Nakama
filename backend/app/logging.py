"""
Structured JSON logging with request ID tracing.

Every request gets an X-Request-ID header (generated if missing).
All logs are emitted as JSON lines for easy parsing by log aggregators.

Usage:
    from app.logging import logger, get_request_id

    logger.info("source_fetch", source="komiku", url=url, duration_ms=123)
    req_id = get_request_id()
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

from starlette.requests import Request

_request_id: ContextVar[str] = ContextVar("request_id", default="")
_request_start: ContextVar[float] = ContextVar("request_start", default=0.0)


def get_request_id() -> str:
    return _request_id.get()


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        obj: Dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id.get() or "-",
        }
        if record.exc_info and record.exc_info[1]:
            obj["exception"] = str(record.exc_info[1])
        return json.dumps(obj, default=str)


def setup_logging():
    """Configure root logger for JSON output."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    # Quiet noisy libs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class RequestLoggingMiddleware:
    """Log every request with method, path, status, duration, and request ID.

    Implemented as a *pure ASGI* middleware (not Starlette's BaseHTTPMiddleware)
    because BaseHTTPMiddleware wraps the response in a body-stream that is
    incompatible with streaming/SSE responses (e.g. the /mcp server). Wrapping
    those raised `AssertionError: Unexpected message: http.response.start` on
    connection teardown. A pure ASGI middleware observes the send events without
    buffering the body, so it works for both normal and streaming responses.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        _request_id.set(req_id)
        start = time.time()
        _request_start.set(start)

        status_code = 500  # default if the app never sends a start message

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                # Inject X-Request-ID into the outgoing headers.
                headers = message.setdefault("headers", [])
                headers.append((b"x-request-id", req_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.time() - start) * 1000
            logging.getLogger("nakama.request").info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": round(duration_ms, 1),
                    "request_id": req_id,
                },
            )


# Module-level convenience
def log(event: str, **kwargs):
    """Emit a structured log event."""
    logging.getLogger("nakama").info(event, extra=kwargs)
