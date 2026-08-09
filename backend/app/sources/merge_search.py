"""Multi-source search aggregation.

Shared helper for /anime/search, /comic/search, /novel/search.
Fans out to every registered source concurrently, deduplicates by
normalized title (falling back to title+author), returns a unified
list sorted by source coverage then source quality.
"""
from __future__ import annotations
import asyncio
import re
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Tuple

# Which source "wins" when two normalized titles collide. Lower = preferred
# (better metadata / more stable IDs / cleaner data). Used to pick the
# representative item fields when merging duplicates across sources.
SOURCE_RANK: Dict[str, int] = {
    # Anime — metadata-first, stable
    "anilist": 0,
    "jikan": 1,
    "kura": 2,
    "otakudesu": 3,
    "samehadaku": 4,
    "anichin": 5,
    "anoboy": 6,
    # Comic — official API first, then stable ID scrapers
    "mangadex": 0,
    "kiryuu": 1,
    "komiku": 2,
    "komikindo": 3,
    "shinigami": 4,
    "komikcast": 5,
    "bacakomik": 6,
    "komikstation": 7,
    "westmanga": 8,
    # Novel
    "novelbin": 1,
    "novelfull": 2,
    "sakuranovel": 3,
    "meionovels": 4,
    "novelhubapp": 5,
}

# Sources NOT ranked above default to a mid-tier rank so unranked sources
# never accidentally win over a known-good primary.
_DEFAULT_RANK = 50


def _source_rank(name: str) -> int:
    return SOURCE_RANK.get(name, _DEFAULT_RANK)


def _strip_accents(s: str) -> str:
    """Remove combining diacritics so 'Áo Kagura' and 'Ao Kagura' collide."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


def _norm_core(part: str) -> str:
    part = _strip_accents(part)
    part = re.sub(r"[\s\W_]+", " ", part.lower()).strip()
    part = re.sub(r"\s+", " ", part)
    return part


def normalize_title(t: str) -> str:
    """Normalize a title for dedup matching (single-source key)."""
    if not t:
        return ""
    t = _norm_core(t)
    t = re.sub(r"\b(episode|ep|chapter|ch)\s*\d+\b", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def dedup_key(item: dict) -> str:
    """Best-effort dedup key: title, or title+author when a single title
    would be too ambiguous. Mirrors Sanka's ``dedupKey = title + author``
    fallback so two different series with the same name survive."""
    title = normalize_title(item.get("title") or item.get("name") or "")
    if not title:
        return ""
    author = normalize_title(item.get("author") or item.get("artist") or "")
    # Only fold author in when both present (avoids splitting the same series
    # just because one source reports an author and another doesn't).
    if author and author not in title:
        return f"{title}|{author}"
    return title

async def multi_source_search(
    *,
    kind: str,
    query: str,
    get_factory: Callable[[str], Any],
    list_fn: Callable[[], List[str]],
    timeout: float = 15.0,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    early_results: int = 0,
) -> Dict[str, Any]:
    """Search every registered source concurrently.

    Returns a dict with: items, sources_queried, sources_failed,
    merged_unique_titles, page, page_size, total.

    If ``early_results`` > 0, returns as soon as that many sources
    complete successfully (fast-path for interactive search). Remaining
    sources are still queried but with a shorter timeout.
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

    # Stagger slow sources (FlareSolverr/Camoufox) by 0.5s to avoid
    # thundering-herd on shared resources and let fast sources return first.
    SLOW_SOURCES = {"sakuranovel", "westmanga", "samehadaku", "anoboy"}
    fast = [s for s in sources if s not in SLOW_SOURCES]
    slow = [s for s in sources if s in SLOW_SOURCES]

    async def _staggered(name: str, delay: float = 0.0):
        if delay > 0:
            await asyncio.sleep(delay)
        return await asyncio.wait_for(_one(name), timeout=timeout)

    # Fast sources start immediately, slow sources get 0.5s stagger
    tasks = [_staggered(s) for s in fast] + [_staggered(s, 0.5) for s in slow]

    if early_results > 0 and len(fast) >= early_results:
        # Early-return path: collect first N fast source results
        done: List[Any] = []
        pending = list(tasks)
        while pending and len([r for r in done if isinstance(r, tuple) and isinstance(r[1], dict) and r[1].get("ok")]) < early_results:
            finished, pending = await asyncio.wait(
                pending, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
            )
            done.extend(finished)
        # Gather remaining in background with short timeout
        if pending:
            remaining, _ = await asyncio.wait(pending, timeout=min(timeout, 8.0))
            done.extend(remaining)
        finished = [t.result() for t in done if t.done() and not t.cancelled()]
    else:
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
            key = dedup_key(item)
            if not key:
                continue
            if key not in merged:
                merged[key] = {
                    **item,
                    "_sources": [],
                    "_source_count": 0,
                    "_best_source": name,
                }
            else:
                # Merge: prefer fields from the higher-ranked source.
                existing = merged[key]
                if _source_rank(name) < _source_rank(existing.get("_best_source", "")):
                    merged[key] = {**existing, **item, "_sources": existing["_sources"]}
                    merged[key]["_best_source"] = name
            merged[key]["_sources"].append(name)
            merged[key]["_source_count"] = len(merged[key]["_sources"])

    items = []
    for m in merged.values():
        items.append({
            **m,
            "_best_source": m.pop("_best_source", ""),
        })
    items.sort(
        key=lambda x: (-x.get("_source_count", 0), x.get("_best_source", ""), x.get("title", "")),
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


async def multi_source_home(
    *,
    kind: str,
    get_factory: Callable[[str], Any],
    list_fn: Callable[[], List[str]],
    timeout: float = 15.0,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Aggregate the ``home()`` listing of every registered source.

    Mirrors multi_source_search but calls each source's home() instead of
    search(query). Fans out concurrently, deduplicates by normalized title,
    merges duplicate titles across sources (annotating _sources), and returns
    a single unified list sorted by source coverage then source quality. This
    is what powers the "one unified list, providers hidden" home page.
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
            results = await src.home()
            return name, {"ok": True, "items": results if isinstance(results, list) else []}
        except Exception as e:
            return name, {"ok": False, "error": str(e)[:200]}

    SLOW_SOURCES = {"sakuranovel", "westmanga", "samehadaku", "anoboy"}
    fast = [s for s in sources if s not in SLOW_SOURCES]
    slow = [s for s in sources if s in SLOW_SOURCES]

    async def _staggered(name: str, delay: float = 0.0):
        if delay > 0:
            await asyncio.sleep(delay)
        return await asyncio.wait_for(_one(name), timeout=timeout)

    tasks = [_staggered(s) for s in fast] + [_staggered(s, 0.5) for s in slow]
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

    merged = _merge_by_title(by_source)

    items = []
    for m in merged.values():
        items.append({**m, "_best_source": m.pop("_best_source", "")})
    items.sort(
        key=lambda x: (-x.get("_source_count", 0), x.get("_best_source", ""), x.get("title", "")),
    )

    paged, total = _paginate(items, page, page_size)
    if isinstance(paged, dict) and paged.get("page_size") is None and page is None:
        result_out: Dict[str, Any] = {
            "items": paged["items"],
            "page": 1,
            "page_size": None,
            "total": total,
        }
    else:
        result_out = paged
    result_out["sources_queried"] = sources
    result_out["sources_failed"] = sources_failed
    result_out["merged_unique_titles"] = len(merged)
    return result_out


def _merge_by_title(by_source: Dict[str, dict]) -> Dict[str, dict]:
    """Deduplicate items across sources by normalized title.

    Prefers fields from the higher-ranked source and annotates each merged
    item with _sources / _source_count / _best_source.
    """
    merged: Dict[str, dict] = {}
    for name, data in by_source.items():
        for item in data.get("items", []):
            if not isinstance(item, dict):
                continue
            key = dedup_key(item)
            if not key:
                continue
            if key not in merged:
                merged[key] = {
                    **item,
                    "_sources": [],
                    "_source_count": 0,
                    "_best_source": name,
                }
            else:
                existing = merged[key]
                if _source_rank(name) < _source_rank(existing.get("_best_source", "")):
                    merged[key] = {**existing, **item, "_sources": existing["_sources"]}
                    merged[key]["_best_source"] = name
            merged[key]["_sources"].append(name)
            merged[key]["_source_count"] = len(merged[key]["_sources"])
    return merged


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
