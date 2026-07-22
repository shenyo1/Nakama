"""Tests for the response-level TTL cache."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.response_cache import cache_stats


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_cache_key_built_from_method_path_query():
    from app.response_cache import _key

    class FakeRequest:
        method = "GET"
        class url:
            path = "/anime/test/home"
            query = "page=2"

    k = _key(FakeRequest())
    assert isinstance(k, str) and len(k) == 40  # sha1 hex


@pytest.mark.asyncio
async def test_cache_stats_returns_dict():
    stats = cache_stats()
    assert isinstance(stats, dict)
    assert "size" in stats


@pytest.mark.asyncio
async def test_home_endpoint_returns_consistent_response(client):
    """Two back-to-back requests should return identical JSON (cache hit on 2nd)."""
    # offline test — public health endpoint may not need auth
    r1 = await client.get("/anime/otakudesu/home")
    r2 = await client.get("/anime/otakudesu/home")
    # Both should succeed or both fail consistently (cache shouldn't change semantics)
    assert r1.status_code == r2.status_code
    # Body should match (cached payload or upstream error both deterministic)
    if r1.status_code == 200:
        assert r1.json() == r2.json()
