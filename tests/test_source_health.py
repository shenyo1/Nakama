"""Tests for /sources/health scoreboard."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.sources import health as health_mod


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_health_state():
    health_mod._STATE.clear()
    yield
    health_mod._STATE.clear()


@pytest.mark.asyncio
async def test_sources_health_passive(client):
    r = await client.get("/sources/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    data = body["data"]
    assert "summary" in data
    assert "sources" in data
    assert data["summary"]["total"] >= 8
    names = {s["name"] for s in data["sources"]}
    assert "kiryuu" in names
    assert "komikcast" in names
    assert "sakuranovel" in names
    # passive snapshot starts unknown
    assert all(s["status"] in ("unknown", "healthy", "degraded", "down") for s in data["sources"])


@pytest.mark.asyncio
async def test_sources_health_records_after_traffic(client):
    # exercise offline fixtures for a comic source
    r = await client.get("/comic/kiryuu/home")
    assert r.status_code == 200
    r2 = await client.get("/sources/health")
    data = r2.json()["data"]
    kiryuu = next(s for s in data["sources"] if s["name"] == "kiryuu")
    assert kiryuu["ok"] >= 1
    assert kiryuu["status"] in ("healthy", "degraded")
    assert kiryuu["last_latency_ms"] is not None


@pytest.mark.asyncio
async def test_source_health_single_probe_offline(client):
    r = await client.get("/sources/health/komiku?probe=true")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["name"] == "komiku"
    assert data["status"] in ("healthy", "degraded", "down", "unknown")
    # offline fixtures should yield healthy for komiku
    assert data["ok"] + data["fail"] >= 1


@pytest.mark.asyncio
async def test_source_health_unknown_404(client):
    r = await client.get("/sources/health/not-a-real-source")
    assert r.status_code == 404
