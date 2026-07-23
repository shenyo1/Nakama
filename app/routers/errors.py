"""Client error reporting — POST /errors from browser, GET /admin/errors for ops.

Replaces Sentry-class error tracking for a $0 budget:
- Frontend catches uncaught exceptions and posts here
- Backend records 500s automatically via exception hook
- Errors stored in Redis (recent 500) + JSONL file (durable)
- Telegram alert on high-severity errors (rate-limited 1/min)
"""
from __future__ import annotations

import json
import os
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from ..config import get_settings
from ..quota import PLAN_QUOTAS
from ..ratelimit import limiter
from ..response_cache import cache_stats
from ..schemas import ApiResponse

router = APIRouter(tags=["ops"])

# In-process ring buffer (last 200 errors). Survives only per worker.
_RECENT: Deque[Dict[str, Any]] = deque(maxlen=200)

# Durable store: append-only JSONL, rotated at ~10 MB. Falls back to /tmp
# when the working directory is read-only (e.g. inside the container).
_ERRORS_DIR_CANDIDATES = [
    Path(os.environ.get("NAKAMA_ERRORS_FILE", "")).parent
    if os.environ.get("NAKAMA_ERRORS_FILE")
    else None,
    Path.cwd() / "data",
    Path("/tmp/nakama-errors"),
]
_ERRORS_DIR = next(
    (d for d in _ERRORS_DIR_CANDIDATES if d and d.exists() and os.access(d, os.W_OK)),
    _ERRORS_DIR_CANDIDATES[-1],
)
try:
    _ERRORS_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    _ERRORS_DIR = Path("/tmp/nakama-errors")
    _ERRORS_DIR.mkdir(parents=True, exist_ok=True)
ERRORS_FILE = _ERRORS_DIR / "errors.jsonl"

# Telegram alert throttling
_LAST_TG_ALERT: Dict[str, float] = {}
_TG_COOLDOWN_SEC = 60.0


class ClientError(BaseModel):
    message: str = Field(..., max_length=1000)
    stack: Optional[str] = Field(None, max_length=5000)
    source: Optional[str] = Field(None, description="frontend route or component name")
    severity: str = Field("error", pattern="^(debug|info|warning|error|critical)$")
    extra: Optional[Dict[str, Any]] = None


@router.post("/errors", response_model=ApiResponse, summary="Report a client-side error")
@limiter.limit(get_settings().rate_limit)
async def report_error(
    body: ClientError,
    request: Request,
    user_agent: Optional[str] = Header(None),
):
    """Called by the browser/Next.js error boundary when something blows up.

    Cheap to call, rate-limited globally, and never raises — a downstream
    error tracker that itself errors is worse than no tracker.
    """
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "epoch": time.time(),
        "kind": "client",
        "message": body.message,
        "stack": body.stack,
        "source": body.source,
        "severity": body.severity,
        "extra": body.extra or {},
        "user_agent": user_agent,
        "ip": request.client.host if request.client else None,
    }
    _record(rec)
    return ApiResponse(data={"recorded": True, "id": len(_RECENT)})


@router.get(
    "/admin/errors",
    response_model=ApiResponse,
    summary="List recent errors (admin)",
)
@limiter.limit(get_settings().rate_limit)
async def list_errors(
    request: Request,
    limit: int = 50,
    severity: Optional[str] = None,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Return the most recent client/server errors. Requires X-API-Key."""
    settings = get_settings()
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="invalid X-API-Key")
    items = list(_RECENT)
    if severity:
        items = [e for e in items if e.get("severity") == severity]
    items.reverse()  # newest first
    return ApiResponse(data={"errors": items[:limit], "total": len(_RECENT)})


def _record(rec: Dict[str, Any]) -> None:
    """Append an error to in-memory ring + JSONL file. Fire-and-forget."""
    _RECENT.append(rec)
    try:
        with ERRORS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass
    # Telegram alert for critical only (rate-limited 1 per minute)
    if rec.get("severity") == "critical":
        _maybe_alert(rec)


def _maybe_alert(rec: Dict[str, Any]) -> None:
    """Send a Telegram alert for critical errors, throttled 1/minute."""
    now = time.time()
    last = _LAST_TG_ALERT.get("critical", 0)
    if now - last < _TG_COOLDOWN_SEC:
        return
    _LAST_TG_ALERT["critical"] = now
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not (token and chat):
        return
    try:
        import urllib.request
        import urllib.parse

        text = (
            f"🚨 Nakama CRITICAL error\n"
            f"kind={rec.get('kind')} src={rec.get('source')}\n"
            f"{rec.get('message', '')[:300]}"
        )
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data,
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def capture_server_error(
    request: Request, exc: Exception, status_code: int = 500
) -> None:
    """Hook called from the global exception handler."""
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "epoch": time.time(),
        "kind": "server",
        "message": f"{type(exc).__name__}: {exc}"[:1000],
        "stack": None,
        "source": f"{request.method} {request.url.path}" if request else None,
        "severity": "critical" if status_code >= 500 else "error",
        "extra": {"status_code": status_code},
        "user_agent": request.headers.get("user-agent") if request else None,
        "ip": request.client.host if request and request.client else None,
    }
    _record(rec)
