"""Tests for new providers + multi-key + CORS config."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.config import get_settings


@pytest.fixture
def api_key_multi():
    s = get_settings()
    orig_key, orig_keys = s.api_key, s.api_keys
    s.api_key = "primary-secret"
    s.api_keys = ["client-a-key", "client-b-key"]
    yield s
    s.api_key = orig_key
    s.api_keys = orig_keys


@pytest.fixture
def cors_strict():
    s = get_settings()
    orig = s.allow_origins
    s.allow_origins = ["https://app.mynakama.web.id"]
    yield s
    s.allow_origins = orig


@pytest.mark.asyncio
async def test_samehadaku_registered():
    from app.sources import list_anime_sources
    assert "samehadaku" in list_anime_sources()


@pytest.mark.asyncio
async def test_komikindo_registered():
    from app.sources import list_comic_sources
    assert "komikindo" in list_comic_sources()


@pytest.mark.asyncio
async def test_novelbin_registered():
    from app.sources import list_novel_sources
    assert "novelbin" in list_novel_sources()


@pytest.mark.asyncio
async def test_multi_api_key_accepted(api_key_multi):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/comic/komiku/home", headers={"X-API-Key": "client-a-key"})
        assert r.status_code == 200
        r2 = await c.get("/comic/komiku/home", headers={"X-API-Key": "client-b-key"})
        assert r2.status_code == 200


@pytest.mark.asyncio
async def test_multi_api_key_rejects_unknown(api_key_multi):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/comic/komiku/home", headers={"X-API-Key": "wrong-key"})
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_cors_strict_origin(monkeypatch):
    import importlib
    import app.main as mainmod
    s = get_settings()
    orig = s.allow_origins
    s.allow_origins = ["https://app.mynakama.web.id"]
    # Rebuild the app so CORSMiddleware picks up the new origin list.
    monkeypatch.setenv("ALLOW_ORIGINS", "https://app.mynakama.web.id")
    importlib.reload(mainmod)
    try:
        async with AsyncClient(transport=ASGITransport(app=mainmod.app), base_url="http://test") as c:
            r = await c.get("/health", headers={"Origin": "https://evil.com"})
            assert r.headers.get("access-control-allow-origin") != "https://evil.com"
            r2 = await c.get("/health", headers={"Origin": "https://app.mynakama.web.id"})
            assert r2.headers.get("access-control-allow-origin") == "https://app.mynakama.web.id"
    finally:
        s.allow_origins = orig
        importlib.reload(mainmod)
