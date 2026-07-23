"""Tests for the cross-source comic fallback router."""
from __future__ import annotations

import hashlib, json, os, pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def _fixture_exists(url: str) -> bool:
    from app.config import get_settings
    get_settings.cache_clear()
    s = get_settings()
    h = hashlib.sha1(f"GET|{url}|{json.dumps({})}".encode()).hexdigest()[:16]
    return os.path.isfile(os.path.join(s.fixtures_dir, f"{h}.html"))


# Check if enough fixtures exist for multi-source search tests
_COMIC_FIXTURES = {
    "komiku": "https://komiku.id/",
    "kiryuu": "https://v7.kiryuu.to/",
    "komikstation": "https://komikstation.org/",
}
_missing = [n for n, u in _COMIC_FIXTURES.items() if not _fixture_exists(u)]
_SKIP_SEARCH = len(_missing) > 1  # allow 1 missing


@pytest.fixture(autouse=True)
def _offline_env(monkeypatch):
    monkeypatch.setenv("OFFLINE_MODE", "1")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("FLARESOLVERR_URL", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.skipif(_SKIP_SEARCH, reason="fixtures missing for multi-source search")
@pytest.mark.network
@pytest.mark.asyncio
async def test_fallback_search_ok(client):
    r = await client.get("/comic/search/solo")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["query"] == "solo"
    assert "primary" in data
    assert isinstance(data["sources_tried"], list)
    assert isinstance(data["results"], dict)
    assert isinstance(data["counts"], dict)


@pytest.mark.skipif(_SKIP_SEARCH, reason="fixtures missing for multi-source search")
@pytest.mark.asyncio
@pytest.mark.network
async def test_fallback_search_with_primary(client):
    r = await client.get("/comic/search/solo?primary=komiku")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["primary"] == "komiku"


@pytest.mark.skipif(_SKIP_SEARCH, reason="fixtures missing for multi-source search")
@pytest.mark.asyncio
@pytest.mark.network
async def test_fallback_search_bad_primary(client):
    r = await client.get("/comic/search/solo?primary=does-not-exist")
    assert r.status_code == 404


@pytest.mark.skipif(_SKIP_SEARCH, reason="fixtures missing for multi-source search")
@pytest.mark.asyncio
@pytest.mark.network
async def test_fallback_manga_offline(client):
    """In offline mode, manga with slug 'solo-leveling' is in komiku fixtures."""
    r = await client.get("/comic/manga/solo-leveling")
    assert r.status_code == 200
    body = r.json()
    data = body["data"]
    assert data["winner"]
    assert "detail" in data
    assert data["matched"] >= 1


@pytest.mark.skipif(_SKIP_SEARCH, reason="fixtures missing for multi-source search")
@pytest.mark.asyncio
@pytest.mark.network
async def test_fallback_manga_with_primary(client):
    r = await client.get("/comic/manga/solo-leveling?primary=kiryuu")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["primary"] == "kiryuu"


@pytest.mark.skipif(_SKIP_SEARCH, reason="fixtures missing for multi-source search")
@pytest.mark.network  # fans out to all sources including Camoufox-dependent westmanga
@pytest.mark.asyncio
async def test_fallback_chapter_returns_metadata_or_502(client):
    """Chapter lookup should return metadata if found, or 502 if no source has it."""
    r = await client.get("/comic/chapter/solo-leveling-chapter-1")
    if r.status_code == 200:
        body = r.json()
        data = body["data"]
        assert data["primary"]
        assert "chapter" in data
        assert "sources_failed" in data
    else:
        assert r.status_code == 502


@pytest.mark.asyncio
async def test_cache_control_header_attached(client):
    """Successful comic listing should advertise Cache-Control for CF."""
    r = await client.get("/comic/komiku/home")
    assert r.status_code == 200
    cc = r.headers.get("cache-control") or r.headers.get("Cache-Control")
    assert cc is not None
    assert "public" in cc
    assert "max-age=60" in cc


@pytest.mark.asyncio
async def test_cache_control_no_store_on_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    cc = r.headers.get("cache-control") or r.headers.get("Cache-Control")
    assert cc is not None
    assert "no-store" in cc