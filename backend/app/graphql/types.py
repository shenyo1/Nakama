"""Strawberry GraphQL types mirroring Nakama's Pydantic response models.

Every type is decorated with @strawberry.type so Strawberry can
introspect fields and generate the GraphQL schema. Optional fields
default to None; list fields default to an empty list.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

import strawberry


# ---------------------------------------------------------------------------
# Shared / enum types
# ---------------------------------------------------------------------------

@strawberry.enum
class ContentKind(Enum):
    ANIME = "anime"
    COMIC = "comic"
    NOVEL = "novel"


# ---------------------------------------------------------------------------
# Anime types
# ---------------------------------------------------------------------------

@strawberry.type
class AnimeSummary:
    title: str
    slug: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    status: Optional[str] = None
    score: Optional[str] = None
    released: Optional[str] = None


@strawberry.type
class AnimeDetail(AnimeSummary):
    japanese_title: Optional[str] = None
    synopsis: Optional[str] = None
    genres: List[str] = strawberry.field(default_factory=list)
    episodes_count: Optional[str] = None
    studios: Optional[str] = None
    episodes: List[strawberry.scalars.JSON] = strawberry.field(default_factory=list)


@strawberry.type
class Episode:
    number: Optional[str] = None
    title: Optional[str] = None
    slug: Optional[str] = None
    url: Optional[str] = None
    date: Optional[str] = None


@strawberry.type
class EpisodeStream:
    resolution: Optional[str] = None
    url: Optional[str] = None


@strawberry.type
class EpisodeDetail:
    anime_title: Optional[str] = None
    episode_number: Optional[str] = None
    streams: List[EpisodeStream] = strawberry.field(default_factory=list)
    downloads: List[EpisodeStream] = strawberry.field(default_factory=list)
    next: Optional[str] = None
    prev: Optional[str] = None


# ---------------------------------------------------------------------------
# Comic types
# ---------------------------------------------------------------------------

@strawberry.type
class ComicSummary:
    title: str
    slug: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    type: Optional[str] = None
    views: Optional[str] = None
    latest_chapter: Optional[str] = None


@strawberry.type
class ComicDetail(ComicSummary):
    author: Optional[str] = None
    status: Optional[str] = None
    genres: List[str] = strawberry.field(default_factory=list)
    synopsis: Optional[str] = None
    chapters: List[strawberry.scalars.JSON] = strawberry.field(default_factory=list)


@strawberry.type
class ChapterImage:
    index: int
    url: Optional[str] = None


@strawberry.type
class ChapterDetail:
    comic_title: Optional[str] = None
    chapter: Optional[str] = None
    url: Optional[str] = None
    images: List[ChapterImage] = strawberry.field(default_factory=list)
    next: Optional[str] = None
    prev: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Novel types
# ---------------------------------------------------------------------------

@strawberry.type
class NovelSummary:
    title: str
    slug: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    rating: Optional[str] = None
    latest_chapter: Optional[str] = None


@strawberry.type
class NovelDetail(NovelSummary):
    author: Optional[str] = None
    synopsis: Optional[str] = None
    genres: List[str] = strawberry.field(default_factory=list)
    chapters: List[strawberry.scalars.JSON] = strawberry.field(default_factory=list)


@strawberry.type
class NovelChapter:
    title: Optional[str] = None
    slug: Optional[str] = None
    url: Optional[str] = None
    date: Optional[str] = None


@strawberry.type
class ChapterText:
    novel_title: Optional[str] = None
    chapter_title: Optional[str] = None
    url: Optional[str] = None
    paragraphs: List[str] = strawberry.field(default_factory=list)
    content: Optional[str] = None
    next: Optional[str] = None
    prev: Optional[str] = None


# ---------------------------------------------------------------------------
# Search result type
# ---------------------------------------------------------------------------

@strawberry.type
class SearchResult:
    """Unified search result that can represent anime, comic, or novel items."""
    title: str
    kind: ContentKind
    slug: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    source: Optional[str] = None
    type: Optional[str] = None       # manga/manhwa/manhua, Light Novel/Web Novel
    status: Optional[str] = None
    score: Optional[str] = None
    rating: Optional[str] = None
    released: Optional[str] = None
    latest_chapter: Optional[str] = None
    views: Optional[str] = None
    # Raw dict for any extra fields not explicitly modelled.
    extra: strawberry.scalars.JSON = strawberry.field(default_factory=dict)


# ---------------------------------------------------------------------------
# Source info type
# ---------------------------------------------------------------------------

@strawberry.type
class SourceInfo:
    name: str
    kind: ContentKind


# ---------------------------------------------------------------------------
# Home page result
# ---------------------------------------------------------------------------

@strawberry.type
class HomeResult:
    source: str
    kind: ContentKind
    items: List[strawberry.scalars.JSON] = strawberry.field(default_factory=list)
