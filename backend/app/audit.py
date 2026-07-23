"""Append-only audit log for authenticated / metered requests."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Query, Request

from .config import get_settings
from .ratelimit import limiter
from .schemas import ApiResponse

router = APIRouter(tags=["ops"])

_CANDIDATES = [
    Path("/data/audit.jsonl"),
    Path("/home/ubuntu/.config/nakama/audit.jsonl"),
    Path.home() / ".config" / "nakama" / "audit.jsonl",
]


def _path() -> Path:
    import os

    env = os.getenv("NAKAMA_AUDIT_FILE")
    if env:
        return Path(env)
    for p in _CANDIDATES:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.exists() or p.parent.exists():
                return p
        except OSError:
            continue
    return _CANDIDATES[0]


def write_audit(event: Dict[str, Any]) -> None:
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **event,
    }
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    for p in {_path(), Path("/data/audit.jsonl"), Path("/home/ubuntu/.config/nakama/audit.jsonl")}:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("a", encoding="utf-8") as f:
                f.write(line)
            break
        except OSError:
            continue


@router.get("/audit", response_model=ApiResponse, summary="Recent audit log entries")
@limiter.limit(get_settings().rate_limit)
async def audit_tail(request: Request, limit: int = Query(50, ge=1, le=500)):
    path = _path()
    rows: List[dict] = []
    if path.exists():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError:
            rows = []
    rows.reverse()
    return ApiResponse(data={"path": str(path), "count": len(rows), "events": rows})
