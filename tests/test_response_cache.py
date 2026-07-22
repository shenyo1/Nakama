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
    assert "backend" in stats
    assert stats["backend"] in ("memory", "redis")


@pytest.mark.asyncio
async def test_cache_backend_defaults_to_memory(monkeypatch):
    """Without RESPONSE_CACHE_REDIS_URL env, backend should be 'memory'."""
    # Read the module-level state directly without reload (reload pollutes other tests).
    import app.response_cache as rc
    if "RESPONSE_CACHE_REDIS_URL" not in __import__("os").environ:
        assert rc._BACKEND_KIND == "memory"
        assert rc.cache_stats()["backend"] == "memory"


@pytest.mark.asyncio
async def test_cache_backend_redis_when_env_set():
    """With RESPONSE_CACHE_REDIS_URL, backend should be 'redis'.
    We test the build function directly without module-level reload.
    """
    import os
    import app.response_cache as rc
    old = os.environ.pop("RESPONSE_CACHE_REDIS_URL", None)
    kind, url = rc._build_backend()
    assert kind == "memory"
    os.environ["RESPONSE_CACHE_REDIS_URL"] = "redis://localhost:6379/15"
    kind, url = rc._build_backend()
    assert kind == "redis"
    assert url == "redis://localhost:6379/15"
    # Restore
    if old:
        os.environ["RESPONSE_CACHE_REDIS_URL"] = old
    else:
        os.environ.pop("RESPONSE_CACHE_REDIS_URL", None)


@pytest.mark.asyncio
async def test_home_endpoint_returns_consistent_response(client):
    """Two back-to-back requests should return identical JSON (cache hit on 2nd)."""
    r1 = await client.get("/anime/otakudesu/home")
    r2 = await client.get("/anime/otakudesu/home")
    assert r1.status_code == r2.status_code
    if r1.status_code == 200:
        assert r1.json() == r2.json()
