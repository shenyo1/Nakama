"""Shared pagination helpers for list endpoints.

List endpoints accept optional ``page`` and ``page_size`` query params:
- When *both* are omitted → return the plain list (backward-compatible).
- When either is provided → return a ``Paginated`` envelope with the slice.
"""
from __future__ import annotations

from typing import Any, List, Optional, TypeVar

from fastapi import Query

from ..config import get_settings
from ..schemas import Paginated

T = TypeVar("T")


def pagination_params(
    page: Optional[int] = Query(None, ge=1, description="1-indexed page number; omit to disable pagination"),
    page_size: Optional[int] = Query(None, ge=1, description="Items per page (clamped to MAX_PAGE_SIZE); omit to disable"),
) -> tuple[Optional[int], Optional[int]]:
    """Return (page, page_size), with page_size clamped to MAX_PAGE_SIZE.

    Returning ``None`` for both disables pagination at the call site so that
    existing callers see the un-paginated list as before.
    """
    if page is None and page_size is None:
        return None, None
    page = page or 1
    s = get_settings()
    page_size = page_size or s.default_page_size
    if page_size > s.max_page_size:
        page_size = s.max_page_size
    return page, page_size


def paginate(items: List[Any], page: Optional[int], page_size: Optional[int], kind: str = "", source: str = "") -> Any:
    """Return ``items`` unchanged when pagination is off, else a Paginated slice.

    Also enriches each item with ``type`` and ``total_chapters`` fields
    when they're missing, using ``kind`` and ``source`` for context.
    """
    # Enrich items before pagination
    if kind:
        from ..enrich import enrich_home_item
        items = [enrich_home_item(it, kind, source) if isinstance(it, dict) else it for it in items]

    if page is None and page_size is None:
        return items
    s = get_settings()
    page = page or 1
    page_size = page_size or s.default_page_size
    if page_size > s.max_page_size:
        page_size = s.max_page_size
    start = (page - 1) * page_size
    end = start + page_size
    return Paginated[Any](
        items=items[start:end],
        page=page,
        page_size=page_size,
        total=len(items),
    )
