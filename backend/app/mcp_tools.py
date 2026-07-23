"""Custom MCP tools for AI agents — high-level operations beyond simple REST.

These tools expose composite operations that would otherwise require multiple
API calls from an AI agent. They are registered as MCP tools alongside the
auto-generated endpoint tools.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List

from .sources import (
    anime_source,
    comic_source,
    list_anime_sources,
    list_comic_sources,
    list_novel_sources,
    novel_source,
)
from .sources.merge_search import normalize_title


async def mcp_multi_search(query: str, kinds: str = "comic,anime,novel") -> Dict[str, Any]:
    """Search across ALL source types at once and return merged, deduplicated results.

    This is the most comprehensive search: it fans out to every anime, comic,
    and novel source, merges by normalized title, and ranks by coverage.

    Args:
        query: Free-text search query
        kinds: Comma-separated list of types to search (default: all)

    Returns:
        Merged results sorted by source coverage, with per-type breakdowns.
    """
    kind_list = [k.strip() for k in kinds.split(",") if k.strip()]
    results: Dict[str, Any] = {"query": query, "by_type": {}}
    all_merged: Dict[str, dict] = {}

    for kind in kind_list:
        if kind == "anime":
            sources = list_anime_sources()
            factory = anime_source
        elif kind == "comic":
            sources = list_comic_sources()
            factory = comic_source
        elif kind == "novel":
            sources = list_novel_sources()
            factory = novel_source
        else:
            continue

        async def _one(name: str):
            src = factory(name)
            if src is None:
                return name, []
            try:
                return name, await src.search(query)
            except Exception:
                return name, []

        tasks = [asyncio.wait_for(_one(s), timeout=15.0) for s in sources]
        finished = await asyncio.gather(*tasks, return_exceptions=True)

        kind_results: Dict[str, list] = {}
        for result in finished:
            if isinstance(result, tuple) and len(result) == 2:
                name, items = result
                if isinstance(items, list) and items:
                    kind_results[name] = items
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        title = item.get("title") or item.get("name") or ""
                        key = normalize_title(title)
                        if not key:
                            continue
                        if key not in all_merged:
                            all_merged[key] = {**item, "_sources": [], "_types": set()}
                        all_merged[key]["_sources"].append(name)
                        all_merged[key]["_types"].add(kind)

        results["by_type"][kind] = {
            "sources_with_results": list(kind_results.keys()),
            "total_items": sum(len(v) for v in kind_results.values()),
        }

    # Convert _types sets to lists for JSON serialization
    merged_list = []
    for item in all_merged.values():
        item["_types"] = list(item.get("_types", set()))
        item["_source_count"] = len(item.get("_sources", []))
        merged_list.append(item)

    merged_list.sort(key=lambda x: (-x.get("_source_count", 0), x.get("title", "")))
    results["merged_results"] = merged_list[:50]  # Top 50 for MCP context
    results["total_unique"] = len(merged_list)
    return results


async def mcp_source_overview() -> Dict[str, Any]:
    """Get a complete overview of all sources: status, capabilities, and health.

    Returns a structured summary suitable for AI agents to understand what
    data is available and from where.

    Returns:
        Source registry with capabilities per source.
    """
    overview: Dict[str, Any] = {"sources": {}}
    for kind, list_fn, factory in [
        ("anime", list_anime_sources, anime_source),
        ("comic", list_comic_sources, comic_source),
        ("novel", list_novel_sources, novel_source),
    ]:
        for name in list_fn():
            src = factory(name)
            meta = getattr(src, "meta", None) if src else None
            overview["sources"][name] = {
                "kind": kind,
                "name": name,
                "base_url": getattr(src, "base_url", "") if src else "",
                "version": getattr(meta, "version", "1.0") if meta else "1.0",
                "capabilities": {
                    "home": hasattr(src, "home") if src else False,
                    "search": hasattr(src, "search") if src else False,
                    "detail": hasattr(src, "manga") or hasattr(src, "anime") or hasattr(src, "novel") if src else False,
                    "chapter": hasattr(src, "chapter") or hasattr(src, "episode") if src else False,
                },
            }
    overview["total_sources"] = len(overview["sources"])
    return overview


async def mcp_trending(kind: str = "comic", limit: int = 10) -> Dict[str, Any]:
    """Get trending/popular items from the top sources of a given kind.

    Fetches home listings from the top 3 sources and returns the most
    recently updated items across all of them.

    Args:
        kind: anime, comic, or novel
        limit: Max items to return (default 10)

    Returns:
        Trending items with source attribution.
    """
    if kind == "anime":
        sources = list_anime_sources()[:3]
        factory = anime_source
    elif kind == "comic":
        sources = list_comic_sources()[:3]
        factory = comic_source
    elif kind == "novel":
        sources = list_novel_sources()[:3]
        factory = novel_source
    else:
        return {"error": f"Unknown kind '{kind}'. Use: anime, comic, novel"}

    async def _home(name: str):
        src = factory(name)
        if src is None:
            return name, []
        try:
            return name, await src.home()
        except Exception:
            return name, []

    tasks = [asyncio.wait_for(_home(s), timeout=15.0) for s in sources]
    finished = await asyncio.gather(*tasks, return_exceptions=True)

    all_items: List[dict] = []
    for result in finished:
        if isinstance(result, tuple) and len(result) == 2:
            name, items = result
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        item["_source"] = name
                        all_items.append(item)

    return {
        "kind": kind,
        "sources_queried": sources,
        "total_items": len(all_items),
        "trending": all_items[:limit],
    }
