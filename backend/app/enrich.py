"""
Response enrichment — adds missing fields to source responses.

When a source returns home/search results without certain fields
(type, status, total_chapters, author, etc.), this module enriches
them with data we can derive or fetch.

Strategy:
- type: from the source kind (anime/comic/novel) — always available
- status: try to extract from title text (e.g., "Completed", "Ongoing")
- total_chapters: computed from detail page chapters list (cached)
- author: fetched from detail page if missing
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Cache for detail lookups to avoid repeated fetches
_DETAIL_CACHE: Dict[str, Dict[str, Any]] = {}


def enrich_home_item(item: dict, kind: str, source_name: str) -> dict:
    """Add missing fields to a home/search result item."""
    # type — always available from source kind
    if "type" not in item or not item.get("type"):
        item["type"] = kind

    # total_chapters — if chapters list exists, count them
    if "chapters" in item and isinstance(item["chapters"], list):
        if not item.get("total_chapters"):  # None, 0, or missing
            item["total_chapters"] = len(item["chapters"])
    if "episodes" in item and isinstance(item["episodes"], list):
        if not item.get("total_episodes"):  # None, 0, or missing
            item["total_episodes"] = len(item["episodes"])

    # status — try to extract from title or existing data
    if "status" not in item or not item.get("status"):
        item["status"] = _guess_status(item)

    return item


def enrich_detail(detail: dict, kind: str, source_name: str) -> dict:
    """Add missing fields to a detail response."""
    # type
    if "type" not in detail or not detail.get("type"):
        detail["type"] = kind

    # total_chapters from chapters list
    if "chapters" in detail and isinstance(detail["chapters"], list):
        if not detail.get("total_chapters"):  # None, 0, or missing
            detail["total_chapters"] = len(detail["chapters"])
    if "episodes" in detail and isinstance(detail["episodes"], list):
        if not detail.get("total_episodes"):  # None, 0, or missing
            detail["total_episodes"] = len(detail["episodes"])

    # status
    if "status" not in detail or not detail.get("status"):
        detail["status"] = _guess_status(detail)

    return detail


def _guess_status(item: dict) -> Optional[str]:
    """Try to guess the status from title, genres, or other fields."""
    title = str(item.get("title", "")).lower()
    # Common completion markers in Indonesian/English titles
    if any(w in title for w in ("tamat", "completed", "complete", "end", "final")):
        return "completed"
    if any(w in title for w in ("ongoing", "berjalan", "on-going")):
        return "ongoing"

    # Check if chapters count suggests completed
    total = item.get("total_chapters") or item.get("total_episodes")
    if total and isinstance(total, int):
        # Many sites mark completed series with a specific chapter count
        # This is heuristic — not always accurate
        pass

    # Check if there's a status field already in a different key
    for k in ("status_desc", "novelStatusDesc", "bookStatus"):
        if k in item and item[k]:
            return str(item[k]).lower()

    return None
