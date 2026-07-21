"""Tier 3 analytics + postgres readiness smoke tests."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_analytics_endpoint(client):
    r = await client.get("/analytics")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    data = body["data"]
    assert "requests" in data
    assert "cost_guard" in data
    assert "cache_policy" in data
    assert data["cache_policy"]["anime_comic_max_age"] == 60


@pytest.mark.asyncio
async def test_health_backend_field(client):
    r = await client.get("/sources/health")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data.get("backend") in ("memory", "redis")
