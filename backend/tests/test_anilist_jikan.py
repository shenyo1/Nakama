"""Tests for AniList + Jikan anime metadata sources.

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
async def test_anilist_registered(client):
    r = await client.get("/health")
    assert "anilist" in r.json()["data"]["anime_sources"]


@pytest.mark.asyncio
async def test_anilist_home(client):
    r = await client.get("/anime/anilist/home")
    assert r.status_code == 200
    data = r.json()["data"]
    if isinstance(data, dict):
        data = data.get("items", [])
    assert len(data) >= 5
    assert data[0]["title"]


@pytest.mark.asyncio
async def test_anilist_search(client):
    r = await client.get("/anime/anilist/search/boruto")
    assert r.status_code == 200
    items = r.json()["data"]
    if isinstance(items, dict):
        items = items.get("items", [])
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_anilist_detail(client):
    r = await client.get("/anime/anilist/detail/1")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["title"]
    assert data["studios"]


@pytest.mark.asyncio
async def test_anilist_genres(client):
    r = await client.get("/anime/anilist/genres")
    assert r.status_code == 200
    items = r.json()["data"]
    assert isinstance(items, list)
    assert len(items) > 0


@pytest.mark.asyncio
async def test_anilist_genre_listing(client):
    r = await client.get("/anime/anilist/genre/action")
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_jikan_registered(client):
    r = await client.get("/health")
    assert "jikan" in r.json()["data"]["anime_sources"]


@pytest.mark.asyncio
async def test_jikan_home(client):
    r = await client.get("/anime/jikan/home")
    assert r.status_code == 200
    data = r.json()["data"]
    if isinstance(data, dict):
        data = data.get("items", [])
    assert len(data) >= 1
    assert data[0]["title"]


@pytest.mark.asyncio
async def test_jikan_detail(client):
    r = await client.get("/anime/jikan/detail/1")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["title"]
    assert data["score"] is not None


@pytest.mark.asyncio
async def test_jikan_genres(client):
    r = await client.get("/anime/jikan/genres")
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) > 0


@pytest.mark.asyncio
async def test_jikan_season_now(client):
    # /anime/{source}/home == popular (same endpoint alias for top anime).
    r = await client.get("/anime/jikan/home")
    assert r.status_code == 200
    data = r.json()["data"]
    if isinstance(data, dict):
        data = data.get("items", [])
    assert len(data) >= 1