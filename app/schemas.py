"""Pydantic response models.

Every endpoint returns data shaped by these models so the JSON contract is
stable and self-documenting in OpenAPI/Swagger.
"""
from __future__ import annotations

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard envelope returned by every endpoint."""

    ok: bool = True
    source: Optional[str] = None
    data: T


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
    detail: Optional[str] = None


class Paginated(BaseModel, Generic[T]):
    items: List[T]
    page: int
    page_size: int
    total: Optional[int] = None


class Thumbnail(BaseModel):
    url: Optional[str] = None


class AnimeSummary(BaseModel):
    title: str
    slug: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    status: Optional[str] = None
    score: Optional[str] = None
    released: Optional[str] = None


class AnimeDetail(AnimeSummary):
    japanese_title: Optional[str] = None
    synopsis: Optional[str] = None
    genres: List[str] = []
    episodes_count: Optional[str] = None
    studios: Optional[str] = None
    # Episode list (title/slug/url dicts). Kept loose as List[dict] so sources
    # can extend the entry shape without a schema churn.
    episodes: List[dict] = []


class Episode(BaseModel):
    number: Optional[str] = None
    title: Optional[str] = None
    slug: Optional[str] = None
    url: Optional[str] = None
    date: Optional[str] = None


class EpisodeStream(BaseModel):
    resolution: Optional[str] = None
    url: Optional[str] = None


class EpisodeDetail(BaseModel):
    anime_title: Optional[str] = None
    episode_number: Optional[str] = None
    streams: List[EpisodeStream] = []
    downloads: List[EpisodeStream] = []
    next: Optional[str] = None
    prev: Optional[str] = None


class ComicSummary(BaseModel):
    title: str
    slug: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    type: Optional[str] = None  # manga / manhwa / manhua
    views: Optional[str] = None
    latest_chapter: Optional[str] = None


class ComicDetail(ComicSummary):
    author: Optional[str] = None
    status: Optional[str] = None
    genres: List[str] = []
    synopsis: Optional[str] = None
    chapters: List[dict] = []


class ChapterImage(BaseModel):
    index: int
    url: Optional[str] = None


class ChapterDetail(BaseModel):
    comic_title: Optional[str] = None
    chapter: Optional[str] = None
    url: Optional[str] = None
    images: List[ChapterImage] = []
    next: Optional[str] = None
    prev: Optional[str] = None
    # Optional machine-readable notes (e.g. images gated by upstream auth).
    notes: Optional[str] = None


class Genre(BaseModel):
    name: str
    slug: Optional[str] = None
    url: Optional[str] = None


# ---------------------------------------------------------------------------
# Novel schemas
# ---------------------------------------------------------------------------

class NovelSummary(BaseModel):
    """Card/listing entry for a novel."""
    title: str
    slug: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    type: Optional[str] = None  # Light Novel / Web Novel
    status: Optional[str] = None
    rating: Optional[str] = None
    latest_chapter: Optional[str] = None


class NovelDetail(NovelSummary):
    """Full detail page for a single novel (metadata + chapter list)."""
    author: Optional[str] = None
    synopsis: Optional[str] = None
    genres: List[str] = []
    # Chapter list (title/slug/url/date dicts). Loose as List[dict] so sources
    # can extend without a schema churn — matches AnimeDetail/ComicDetail.
    chapters: List[dict] = []


class NovelChapter(BaseModel):
    """A single chapter reference in a chapter list."""
    title: Optional[str] = None
    slug: Optional[str] = None
    url: Optional[str] = None
    date: Optional[str] = None


class ChapterText(BaseModel):
    """Chapter prose — the actual text content of a novel chapter.

    Novel chapters are *text*, so this carries the novel title, chapter title,
    and the body as a list of paragraph strings (preserving the upstream
    paragraph structure). ``content`` is a convenience full-text field.
    """
    novel_title: Optional[str] = None
    chapter_title: Optional[str] = None
    url: Optional[str] = None
    paragraphs: List[str] = []
    content: Optional[str] = None
    next: Optional[str] = None
    prev: Optional[str] = None
