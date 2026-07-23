"""Tests for the persistent user preferences router.

Each test uses a unique username (UUID suffix) so test ordering doesn't
matter and we never need to wipe the SQLite file mid-run.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def _unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _signup_and_login(client: AsyncClient, username: str, password: str) -> str:
    r = await client.post("/auth/register", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    r = await client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_preferences_get_creates_empty(client):
    token = await _signup_and_login(client, _unique("prefsuser1"), "supersecret123")
    r = await client.get("/preferences", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["payload"] == {}


@pytest.mark.asyncio
async def test_preferences_put_replaces(client):
    token = await _signup_and_login(client, _unique("prefsuser2"), "supersecret123")
    # PUT
    r = await client.put(
        "/preferences",
        json={"payload": {"theme": "dark", "font_size": "lg"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["payload"] == {"theme": "dark", "font_size": "lg"}
    # GET round-trip
    r2 = await client.get("/preferences", headers={"Authorization": f"Bearer {token}"})
    assert r2.json()["payload"] == {"theme": "dark", "font_size": "lg"}


@pytest.mark.asyncio
async def test_preferences_patch_merges(client):
    token = await _signup_and_login(client, _unique("prefsuser3"), "supersecret123")
    await client.put(
        "/preferences",
        json={"payload": {"theme": "dark", "lang": "id"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.patch(
        "/preferences",
        json={"payload": {"font_size": "lg"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()["payload"]
    assert body == {"theme": "dark", "lang": "id", "font_size": "lg"}


@pytest.mark.asyncio
async def test_preferences_delete_resets(client):
    token = await _signup_and_login(client, _unique("prefsuser4"), "supersecret123")
    await client.put(
        "/preferences",
        json={"payload": {"theme": "dark"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.delete("/preferences", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["payload"] == {}


@pytest.mark.asyncio
async def test_preferences_requires_auth(client):
    r = await client.get("/preferences")
    assert r.status_code == 401
    r = await client.put("/preferences", json={"payload": {"x": 1}})
    assert r.status_code == 401