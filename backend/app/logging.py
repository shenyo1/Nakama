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

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

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


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, duration, and request ID."""

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        _request_id.set(req_id)
        _request_start.set(time.time())

        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id

        duration_ms = (time.time() - _request_start.get()) * 1000
        logging.getLogger("nakama.request").info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 1),
                "request_id": req_id,
            },
        )
        return response


# Module-level convenience
def log(event: str, **kwargs):
    """Emit a structured log event."""
    logging.getLogger("nakama").info(event, extra=kwargs)
