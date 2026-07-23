"""Tier 5 bookmarks / recommend / trending / webhooks tests."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client: AsyncClient, username: str = "tier5_user") -> str:
    r = await client.post(
        "/auth/register", json={"username": username, "password": "password123"}
    )
    if r.status_code == 409:
        r = await client.post(
            "/auth/login", json={"username": username, "password": "password123"}
        )
    assert r.status_code == 200
    return r.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_bookmarks_crud(client):
    token = await _login(client, "bm_user")
    h = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/bookmarks",
        headers=h,
        json={
            "source": "mangadex",
            "content_id": "solo-leveling",
            "content_type": "comic",
            "title": "Solo Leveling",
        },
    )
    assert r.status_code == 201
    bid = r.json()["data"]["id"]

    lst = await client.get("/bookmarks", headers=h)
    assert lst.status_code == 200
    assert any(x["id"] == bid for x in lst.json()["data"])

    d = await client.delete(f"/bookmarks/{bid}", headers=h)
    assert d.status_code == 200
    assert d.json()["data"]["deleted"] == bid


@pytest.mark.asyncio
async def test_bookmarks_require_jwt(client):
    r = await client.get("/bookmarks")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_webhooks_crud(client):
    token = await _login(client, "wh_user")
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/webhooks",
        headers=h,
        json={"url": "https://example.com/hook", "source": "mangadex"},
    )
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["secret"]
    wid = data["id"]

    lst = await client.get("/webhooks", headers=h)
    assert lst.status_code == 200
    assert any(x["id"] == wid for x in lst.json()["data"])

    d = await client.delete(f"/webhooks/{wid}", headers=h)
    assert d.status_code == 200


@pytest.mark.asyncio
async def test_recommend_and_trending_offline(client):
    # open access in tests (API_KEY unset) — still metered as anon free
    r = await client.get("/recommend/anime")
    # offline fixtures may still return items from anilist fixture path, or 502 if network
    assert r.status_code in (200, 502)
    r2 = await client.get("/trending/comic")
    assert r2.status_code in (200, 502)
