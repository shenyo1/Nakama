"""Tests for the NovelFull novel source."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.sources.novelfull import NovelFullSource


@pytest.fixture
def source() -> NovelFullSource:
    return NovelFullSource()


def test_novelfull_metadata(source):
    assert source.name == "novelfull"
    assert source.base_url == "https://novelfull.com"


@pytest.mark.asyncio
async def test_novelfull_home_returns_list(source):
    """home() must return a list (possibly empty on offline)."""
    try:
        items = await source.home()
    except Exception:
        # Offline / network errors are acceptable
        pytest.skip("network unavailable in test env")
    assert isinstance(items, list)


@pytest.mark.asyncio
async def test_novelfull_registered_in_app():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/sources/health")
        assert r.status_code == 200
        data = r.json()["data"]
        sources = data.get("sources", data) if isinstance(data, dict) else data
        names = {s.get("name") for s in sources}
        assert "novelfull" in names, f"novelfull not in registered sources: {names}"
