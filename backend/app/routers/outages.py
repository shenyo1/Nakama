"""Recent outage history from ~/.config/nakama/outages.jsonl."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Query, Request

from ..config import get_settings
from ..ratelimit import limiter
from ..schemas import ApiResponse

router = APIRouter(tags=["ops"])

_DEFAULT_OUTAGES = Path.home() / ".config" / "nakama" / "outages.jsonl"
# Inside container the home may differ; also check host-mounted path via env.
_OUTAGES_CANDIDATES = [
    Path("/data/outages.jsonl"),
    Path("/home/ubuntu/.config/nakama/outages.jsonl"),
    _DEFAULT_OUTAGES,
]


def _outages_path() -> Path:
    import os

    env = os.getenv("NAKAMA_OUTAGES_FILE")
    if env:
        return Path(env)
    for p in _OUTAGES_CANDIDATES:
        if p.exists():
            return p
    return _OUTAGES_CANDIDATES[0]


@router.get("/outages", response_model=ApiResponse, summary="Recent outage / recovery events")
@limiter.limit(get_settings().rate_limit)
async def outages(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
):
    """Return the tail of the outages JSONL log (newest last, then reversed)."""
    path = _outages_path()
    rows: List[Dict[str, Any]] = []
    if path.exists():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            for line in lines[-limit:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError:
            rows = []
    rows.reverse()  # newest first
    down = sum(1 for r in rows if r.get("event") == "down")
    recovered = sum(1 for r in rows if r.get("event") == "recovered")
    return ApiResponse(
        data={
            "path": str(path),
            "count": len(rows),
            "down_events": down,
            "recovered_events": recovered,
            "events": rows,
        }
    )
