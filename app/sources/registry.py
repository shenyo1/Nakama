"""Registry of available sources, keyed by short name used in the URL path."""
from __future__ import annotations

from typing import Dict, Optional

from .base import AnimeSource, ComicSource, NovelSource

_REGISTRY: Dict[str, object] = {}
_INITIALIZED = False


def _build() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    from .komiku import KomikuSource
    from .kiryuu import KiryuuSource
    from .komikcast import KomikcastSource
    from .mangadex import MangadexSource
    from .sakuranovel import SakuranovelSource
    from .shinigami import ShinigamiSource
    from .otakudesu import OtakudesuSource
    from .anilist import AnilistSource
    from .jikan import JikanSource

    _REGISTRY["komiku"] = KomikuSource()
    _REGISTRY["kiryuu"] = KiryuuSource()
    _REGISTRY["komikcast"] = KomikcastSource()
    _REGISTRY["mangadex"] = MangadexSource()
    _REGISTRY["shinigami"] = ShinigamiSource()
    _REGISTRY["sakuranovel"] = SakuranovelSource()
    # Adult-only sources (nekopoi, mangasusuku) intentionally excluded.
    _REGISTRY["kura"] = OtakudesuSource()  # otakudesu exposed under the "kura" alias
    _REGISTRY["otakudesu"] = OtakudesuSource()
    _REGISTRY["anilist"] = AnilistSource()
    _REGISTRY["jikan"] = JikanSource()
    _INITIALIZED = True


def anime_source(name: str) -> Optional[AnimeSource]:
    _build()
    src = _REGISTRY.get(name)
    return src if isinstance(src, AnimeSource) else None


def comic_source(name: str) -> Optional[ComicSource]:
    _build()
    src = _REGISTRY.get(name)
    return src if isinstance(src, ComicSource) else None


def novel_source(name: str) -> Optional[NovelSource]:
    _build()
    src = _REGISTRY.get(name)
    return src if isinstance(src, NovelSource) else None


def list_anime_sources() -> list[str]:
    _build()
    return [n for n, s in _REGISTRY.items() if isinstance(s, AnimeSource)]


def list_comic_sources() -> list[str]:
    _build()
    return [n for n, s in _REGISTRY.items() if isinstance(s, ComicSource)]


def list_novel_sources() -> list[str]:
    _build()
    return [n for n, s in _REGISTRY.items() if isinstance(s, NovelSource)]
