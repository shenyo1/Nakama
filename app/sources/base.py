"""Base adapter every source (anime/comic) implements."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class SourceError(Exception):
    """Raised when a source fails to return usable data."""


class AnimeSource(ABC):
    """Contract for an anime data source."""

    name: str = "anime"
    base_url: str = ""

    @abstractmethod
    async def home(self) -> List[dict]:
        ...

    @abstractmethod
    async def search(self, query: str) -> List[dict]:
        ...

    @abstractmethod
    async def detail(self, slug: str) -> dict:
        ...

    @abstractmethod
    async def episode(self, slug: str) -> dict:
        ...

    @abstractmethod
    async def genres(self) -> List[dict]:
        ...

    @abstractmethod
    async def genre(self, slug: str) -> List[dict]:
        ...


class NovelSource(ABC):
    """Contract for a web/light novel data source.

    A novel source returns *text* content (chapter prose), not images. The
    adapter is responsible for fetching the upstream HTML and turning it into
    the schema-shaped dicts the router returns.

    Methods:
      home(page)   — latest/featured novels, paginated upstream.
      search(q)    — free-text search.
      detail(slug) — single novel: metadata + chapter list.
      chapter(slug)— chapter prose (list of paragraphs).
      genres()     — all genres.
      genre(slug,page) — novels within a genre, paginated upstream.
      popular()    — popular/ranked novels.
    """

    name: str = "novel"
    base_url: str = ""

    @abstractmethod
    async def home(self, page: int = 1) -> List[dict]:
        ...

    @abstractmethod
    async def search(self, query: str) -> List[dict]:
        ...

    @abstractmethod
    async def detail(self, slug: str) -> dict:
        ...

    @abstractmethod
    async def chapter(self, slug: str) -> dict:
        """Return chapter prose (ChapterText-shaped dict)."""
        ...

    @abstractmethod
    async def genres(self) -> List[dict]:
        ...

    @abstractmethod
    async def genre(self, slug: str, page: int = 1) -> List[dict]:
        ...

    @abstractmethod
    async def popular(self) -> List[dict]:
        ...


class ComicSource(ABC):
    """Contract for a comic/manga data source."""

    name: str = "comic"
    base_url: str = ""

    @abstractmethod
    async def home(self) -> List[dict]:
        ...

    @abstractmethod
    async def search(self, query: str) -> List[dict]:
        ...

    @abstractmethod
    async def manga(self, slug: str) -> dict:
        ...

    @abstractmethod
    async def chapter(self, slug: str) -> dict:
        ...

    @abstractmethod
    async def genre(self, slug: str) -> List[dict]:
        ...
        ...

    @abstractmethod
    async def latest(self) -> List[dict]:
        ...
