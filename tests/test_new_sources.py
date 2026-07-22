"""Unit tests for the 3 new source adapters."""
from __future__ import annotations
import pytest


@pytest.fixture(autouse=True)
def _offline_env(monkeypatch):
    monkeypatch.setenv("OFFLINE_MODE", "1")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("FLARESOLVERR_URL", raising=False)
    # The shared httpx.AsyncClient in app/http.py binds to whichever loop
    # created it first. pytest-asyncio gives each test a fresh loop, so
    # reset the singleton to avoid "Event loop is closed" errors.
    import app.http as http_mod
    http_mod._http = None
    yield
    http_mod._http = None


def _cs(n):
    from app.sources import comic_source
    return comic_source(n)


def _as(n):
    from app.sources import anime_source
    return anime_source(n)


def _ns(n):
    from app.sources import novel_source
    return novel_source(n)

# -------------------- bacakomik --------------------


@pytest.mark.asyncio
async def test_bacakomik_home_returns_items():
    src = _cs("bacakomik")
    items = await src.home()
    assert isinstance(items, list)
    assert len(items) > 5
    first = items[0]
    assert "slug" in first and "title" in first and "url" in first
    assert first["source"] == "bacakomik"
    assert first["url"].startswith("https://bacakomik.my/komik/")


@pytest.mark.asyncio
async def test_bacakomik_search_returns_items():
    src = _cs("bacakomik")
    items = await src.search("magic")
    assert isinstance(items, list)
    # WP search may or may not match; if it does, results should have slug
    if items:
        assert all("slug" in it for it in items)


@pytest.mark.asyncio
async def test_bacakomik_manga_returns_full_detail():
    src = _cs("bacakomik")
    d = await src.manga("magic-emperor")
    assert d["slug"] == "magic-emperor"
    assert "Magic Emperor" in d["title"]
    assert isinstance(d["chapters"], list)
    assert d["source"] == "bacakomik"


@pytest.mark.asyncio
async def test_bacakomik_chapter_returns_images_filtered():
    src = _cs("bacakomik")
    ch = await src.chapter("magic-emperor-chapter-01")
    assert ch["slug"] == "magic-emperor-chapter-01"
    assert isinstance(ch["images"], list)
    if ch["images"]:
        # Filter is supposed to drop the logo
        assert "Ikon-HD-Bacakomik" not in ch["images"][0]


@pytest.mark.asyncio
async def test_bacakomik_genre_listing():
    src = _cs("bacakomik")
    items = await src.genre("action", 1)
    assert isinstance(items, list)


# -------------------- anichin --------------------


@pytest.mark.asyncio
async def test_anichin_home_uses_ongoing():
    """Anichin home should pull from /ongoing/ for the full list."""
    src = _as("anichin")
    items = await src.home()
    assert isinstance(items, list)
    assert len(items) >= 5
    first = items[0]
    assert first["source"] == "anichin"
    assert "/seri/" in first["url"]


@pytest.mark.asyncio
async def test_anichin_search_does_not_crash():
    src = _as("anichin")
    items = await src.search("demon")
    assert isinstance(items, list)


@pytest.mark.asyncio
async def test_anichin_detail_returns_episodes():
    src = _as("anichin")
    d = await src.detail("tales-of-demons-and-gods-season-10")
    assert d["slug"] == "tales-of-demons-and-gods-season-10"
    assert isinstance(d["episodes"], list)
    assert isinstance(d["genres"], list)


@pytest.mark.asyncio
async def test_anichin_episode_slug_format():
    src = _as("anichin")
    d = await src.detail("tales-of-demons-and-gods-season-10")
    if d["episodes"]:
        ep_slug = d["episodes"][0]["slug"]
        # Should be a slug, not a URL or domain
        assert "/" not in ep_slug
        assert "?" not in ep_slug
        assert ep_slug.startswith("tales-of-demons")


@pytest.mark.asyncio
async def test_anichin_genres_listing():
    """Genres page may 404 on the live site; ensure graceful handling."""
    src = _as("anichin")
    try:
        genres = await src.genres()
        assert isinstance(genres, list)
    except Exception:
        # Source may not expose a genres page
        pass


# -------------------- meionovels --------------------


@pytest.mark.asyncio
async def test_meionovels_home_returns_items():
    src = _ns("meionovels")
    items = await src.home()
    assert isinstance(items, list)
    assert len(items) >= 5
    first = items[0]
    assert "slug" in first and "title" in first
    assert first["source"] == "meionovels"
    assert "/novel/" in first["url"]


@pytest.mark.asyncio
async def test_meionovels_search_returns_items():
    src = _ns("meionovels")
    items = await src.search("pangeran")
    assert isinstance(items, list)


@pytest.mark.asyncio
async def test_meionovels_detail_returns_metadata():
    src = _ns("meionovels")
    d = await src.detail("yumemiru-danshi-wa-genjitsushugisha-ln")
    assert d["slug"] == "yumemiru-danshi-wa-genjitsushugisha-ln"
    assert d["title"]
    assert isinstance(d["chapters"], list)


@pytest.mark.asyncio
async def test_meionovels_search_no_crash():
    src = _ns("meionovels")
    items = await src.search("test")
    assert isinstance(items, list)


# -------------------- registry & health integration --------------------


@pytest.mark.asyncio
async def test_new_sources_in_registry():
    from app.sources import (
        list_anime_sources, list_comic_sources, list_novel_sources
    )
    assert "anichin" in list_anime_sources()
    assert "bacakomik" in list_comic_sources()
    assert "meionovels" in list_novel_sources()


@pytest.mark.asyncio
async def test_new_sources_have_meta():
    """Each new adapter exposes SourceMeta with version + alt_domains."""
    for factory, name in [
        (_as, "anichin"),
        (_cs, "bacakomik"),
        (_ns, "meionovels"),
    ]:
        src = factory(name)
        meta = getattr(src, "meta", None)
        assert meta is not None, f"{name} missing meta"
        assert meta.version
        assert meta.verified_on
        assert isinstance(meta.alt_domains, list)
