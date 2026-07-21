"""Tier 4 auth / quota / audit tests."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.config import get_settings
from app.security import hash_password, verify_password, create_access_token, decode_token


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def test_password_hash_roundtrip():
    h = hash_password("hunter2!!")
    assert h.startswith("scrypt$")
    assert verify_password("hunter2!!", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip():
    tok = create_access_token(user_id=7, username="alice", plan="free")
    data = decode_token(tok)
    assert data["sub"] == "7"
    assert data["username"] == "alice"
    assert data["type"] == "access"


@pytest.mark.asyncio
async def test_register_login_me(client):
    r = await client.post(
        "/auth/register", json={"username": "alice_t4", "password": "password123"}
    )
    assert r.status_code in (200, 409)
    if r.status_code == 409:
        r = await client.post(
            "/auth/login", json={"username": "alice_t4", "password": "password123"}
        )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    access = body["data"]["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["data"]["username"] == "alice_t4"


@pytest.mark.asyncio
async def test_jwt_access_protected_route_when_api_key_set(client, api_key_enabled):
    await client.post(
        "/auth/register", json={"username": "bob_t4", "password": "password123"}
    )
    login = await client.post(
        "/auth/login", json={"username": "bob_t4", "password": "password123"}
    )
    assert login.status_code == 200
    access = login.json()["data"]["access_token"]

    r0 = await client.get("/comic/komiku/home")
    assert r0.status_code == 401

    r1 = await client.get(
        "/comic/komiku/home", headers={"Authorization": f"Bearer {access}"}
    )
    assert r1.status_code == 200

    r2 = await client.get(
        "/comic/komiku/home", headers={"X-API-Key": api_key_enabled}
    )
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_audit_endpoint_public(client):
    r = await client.get("/audit")
    assert r.status_code == 200
    assert r.json()["ok"] is True
