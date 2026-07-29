"""GraphQL resolvers that call the existing source adapters.

Each resolver mirrors the REST patterns already established in
``app/routers/*.py`` and ``app/sources/merge_search.py``:
- ``search`` fans out to every source of a given kind concurrently.
- ``detail`` calls a single source's detail/manga method.
- ``home`` calls a single source's home method.
- ``sources`` lists all registered sources with their kind.

All resolvers are async and return Strawberry types from ``.types``.
"""

from __future__ import annotations

import asyncio
from typing import List, Optional

import strawberry

from .types import (
    ChapterDetail,
    ChapterText,
    ComicDetail,
    ContentKind,
    EpisodeDetail,
    HomeResult,
    SearchResult,
    SourceInfo,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_source(kind: str, name: str):
    """Resolve a source adapter by kind and name."""
    from ..sources import anime_source, comic_source, novel_source

    if kind == "anime":
        return anime_source(name)
    if kind == "comic":
        return comic_source(name)
    if kind == "novel":
        return novel_source(name)
    return None


def _list_sources(kind: str) -> List[str]:
    """List registered source names for a given kind."""
    from ..sources import list_anime_sources, list_comic_sources, list_novel_sources

    if kind == "anime":
        return list_anime_sources()
    if kind == "comic":
        return list_comic_sources()
    if kind == "novel":
        return list_novel_sources()
    return []


def _to_search_result(item: dict, kind: ContentKind, source: str) -> SearchResult:
    """Convert a raw source dict into a unified SearchResult."""
    return SearchResult(
        title=item.get("title") or item.get("name") or "",
        kind=kind,
        slug=item.get("slug"),
        url=item.get("url"),
        thumbnail=item.get("thumbnail"),
        source=source,
        type=item.get("type"),
        status=item.get("status"),
        score=item.get("score"),
        rating=item.get("rating"),
        released=item.get("released"),
        latest_chapter=item.get("latest_chapter"),
        views=item.get("views"),
        extra=item,
    )


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------

async def resolve_search(
    query: str,
    kind: ContentKind = ContentKind.COMIC,
    source: Optional[str] = None,
) -> List[SearchResult]:
    """Search across sources of a given kind.

    If *source* is provided, only that source is queried. Otherwise every
    registered source of the given *kind* is searched concurrently.
    """
    kind_str = kind.value  # "anime" | "comic" | "novel"

    if source:
        names = [source]
    else:
        names = _list_sources(kind_str)

    async def _search_one(name: str) -> List[SearchResult]:
        src = _resolve_source(kind_str, name)
        if src is None:
            return []
        try:
            results = await src.search(query)
            if isinstance(results, list):
                return [_to_search_result(r, kind, name) for r in results]
            return []
        except Exception:
            return []

    all_results: List[SearchResult] = []
    if names:
        gathered = await asyncio.gather(*[_search_one(n) for n in names])
        for batch in gathered:
            all_results.extend(batch)

    return all_results


async def resolve_detail(
    slug: str,
    kind: ContentKind,
    source: str,
) -> Optional[strawberry.scalars.JSON]:
    """Fetch detail for a single item from a specific source.

    Returns a JSON scalar so callers get the full source-shaped detail
    without needing a union type for every possible response shape.
    """
    src = _resolve_source(kind.value, source)
    if src is None:
        return None

    try:
        if kind == ContentKind.COMIC:
            result = await src.manga(slug)
        else:
            result = await src.detail(slug)
        return result if isinstance(result, dict) else None
    except Exception:
        return None


async def resolve_home(
    kind: ContentKind,
    source: Optional[str] = None,
) -> List[HomeResult]:
    """Fetch the home page listing for one or all sources of a kind.

    If *source* is provided, only that source is queried. Otherwise every
    registered source of the given *kind* is fetched concurrently.
    """
    kind_str = kind.value

    if source:
        names = [source]
    else:
        names = _list_sources(kind_str)

    async def _home_one(name: str) -> Optional[HomeResult]:
        src = _resolve_source(kind_str, name)
        if src is None:
            return None
        try:
            items = await src.home()
            if isinstance(items, list):
                return HomeResult(source=name, kind=kind, items=items)
            return HomeResult(source=name, kind=kind, items=[])
        except Exception:
            return HomeResult(source=name, kind=kind, items=[])

    results: List[HomeResult] = []
    if names:
        gathered = await asyncio.gather(*[_home_one(n) for n in names])
        for r in gathered:
            if r is not None:
                results.append(r)

    return results


async def resolve_sources() -> List[SourceInfo]:
    """Return all registered sources with their content kind."""
    from ..sources import list_anime_sources, list_comic_sources, list_novel_sources

    result: List[SourceInfo] = []
    for name in list_anime_sources():
        result.append(SourceInfo(name=name, kind=ContentKind.ANIME))
    for name in list_comic_sources():
        result.append(SourceInfo(name=name, kind=ContentKind.COMIC))
    for name in list_novel_sources():
        result.append(SourceInfo(name=name, kind=ContentKind.NOVEL))
    return result
