"""Tests for Kiryuu and Komikcast comic source adapters.

Run with OFFLINE_MODE=1 so sources read local fixtures (no network needed).
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app  # noqa: F401


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_kiryuu_registered(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()["data"]
    assert "kiryuu" in body["comic_sources"]


@pytest.mark.asyncio
async def test_kiryuu_home(client):
    r = await client.get("/comic/kiryuu/home")
    assert r.status_code == 200
    data = r.json()["data"]
    if isinstance(data, dict):
        data = data.get("items", [])
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["title"]


@pytest.mark.asyncio
async def test_kiryuu_manga(client):
    r = await client.get("/comic/kiryuu/manga/solo-leveling")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["title"]
    assert isinstance(data["chapters"], list)
    assert len(data["chapters"]) >= 1


@pytest.mark.asyncio
async def test_kiryuu_chapter(client):
    r = await client.get("/comic/kiryuu/chapter/solo-leveling-chapter-1")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data["images"], list)
    assert len(data["images"]) >= 1


@pytest.mark.asyncio
async def test_komikcast_registered(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()["data"]
    assert "komikcast" in body["comic_sources"]


@pytest.mark.asyncio
async def test_komikcast_home(client):
    r = await client.get("/comic/komikcast/home")
    assert r.status_code == 200
    data = r.json()["data"]
    if isinstance(data, dict):
        data = data.get("items", [])
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["title"]


@pytest.mark.asyncio
async def test_komikcast_manga(client):
    r = await client.get("/comic/komikcast/manga/one-piece")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["title"]
    assert isinstance(data["chapters"], list)
    assert len(data["chapters"]) >= 1


@pytest.mark.asyncio
@pytest.mark.network
async def test_komikcast_chapter(client):
    r = await client.get("/comic/komikcast/chapter/one-piece-chapter-1")
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data["images"], list)
    assert len(data["images"]) >= 1
