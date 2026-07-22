"""Multi-source search aggregation.

Shared helper for /anime/search, /comic/search, /novel/search.
Fans out to every registered source concurrently, deduplicates by
normalized title, returns a unified list sorted by source coverage.
"""
from __future__ import annotations
import asyncio
import re
from typing import Any, Callable, Dict, List, Optional, Tuple


def normalize_title(t: str) -> str:
    """Normalize a title for dedup matching."""
    if not t:
        return ""
    t = re.sub(r"[\s\W_]+", " ", t.lower()).strip()
    t = re.sub(r"\b(episode|ep|chapter|ch)\s*\d+\b", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

async def multi_source_search(
    *,
    kind: str,
    query: str,
    get_factory: Callable[[str], Any],
    list_fn: Callable[[], List[str]],
    timeout: float = 20.0,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Search every registered source concurrently.

    Returns a dict with: items, sources_queried, sources_failed,
    merged_unique_titles, page, page_size, total.
    """
    sources = list_fn()
    if not sources:
        return {
            "items": [],
            "sources_queried": [],
            "sources_failed": [{"source": "*", "error": f"no {kind} sources configured"}],
            "merged_unique_titles": 0,
            "page": page or 1,
            "page_size": page_size,
            "total": 0,
        }

    async def _one(name: str):
        src = get_factory(name)
        if src is None:
            return name, {"error": "not registered"}
        try:
            results = await src.search(query)
            return name, {"ok": True, "items": results if isinstance(results, list) else []}
        except Exception as e:
            return name, {"ok": False, "error": str(e)[:200]}

    tasks = [asyncio.wait_for(_one(s), timeout=timeout) for s in sources]
    finished = await asyncio.gather(*tasks, return_exceptions=True)

    by_source: Dict[str, dict] = {}
    sources_failed: List[dict] = []
    for result in finished:
        if isinstance(result, BaseException):
            sources_failed.append({"source": "?", "error": str(result)[:200]})
            continue
        if not isinstance(result, tuple) or len(result) != 2:
            continue
        name, data = result
        by_source[name] = data
        if not data.get("ok"):
            sources_failed.append({"source": name, "error": data.get("error", "unknown")})

    merged: Dict[str, dict] = {}
    for name, data in by_source.items():
        for item in data.get("items", []):
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("name") or ""
            key = normalize_title(title)
            if not key:
                continue
            if key not in merged:
                merged[key] = {
                    **item,
                    "_sources": [],
                    "_source_count": 0,
                }
            merged[key]["_sources"].append(name)
            merged[key]["_source_count"] = len(merged[key]["_sources"])

    items = sorted(
        merged.values(),
        key=lambda x: (-x.get("_source_count", 0), x.get("title", "")),
    )

    paged, total = _paginate(items, page, page_size)
    if isinstance(paged, dict) and paged.get("page_size") is None and page is None:
        # Caller didn't paginate; build a uniform response
        result: Dict[str, Any] = {
            "items": paged["items"],
            "page": 1,
            "page_size": None,
            "total": total,
        }
    else:
        result = paged
    result["sources_queried"] = sources
    result["sources_failed"] = sources_failed
    result["merged_unique_titles"] = len(merged)
    return result


def _paginate(items: list, page: Optional[int], page_size: Optional[int]) -> Tuple[dict, int]:
    """Return (paged_dict, total). paged_dict has items + page meta.

    A simplified copy of app.routers._pagination.paginate to avoid circular
    import; the routers still wrap this output in their own pagination_params.
    """
    if page is None and page_size is None:
        # Caller wraps in Paginated model if needed
        return ({"items": items, "page": 1, "page_size": None, "total": len(items)}, len(items))
    # Default page-size from settings if needed
    p = page or 1
    # Use a sane default of 24 (matches most sources' first page size)
    ps = page_size or 24
    start = (p - 1) * ps
    end = start + ps
    return ({"items": items[start:end], "page": p, "page_size": ps, "total": len(items)}, len(items))
