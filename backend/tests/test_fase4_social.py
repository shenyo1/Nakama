"""Tests for Fase 4 gamification & social endpoints.

Uses the shared conftest harness (SQLite /tmp DB, OFFLINE_MODE, no API key
-> open access) and registers a real user via the /auth endpoints so XP and
activity actually flow.
"""
from __future__ import annotations

import os

import pytest

from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture()
async def ac():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _register_login(ac: AsyncClient, username: str = "") -> tuple[dict, int]:
    import uuid

    username = username or f"reader{uuid.uuid4().hex[:8]}"
    r = await ac.post("/auth/register", json={"username": username, "password": "sekret123"})
    assert r.status_code in (200, 201), r.text
    data = r.json()["data"]
    tok = data.get("access_token") or data.get("token")
    uid = data.get("user_id") or data.get("id")
    assert tok, f"no token in register: {r.text}"
    assert uid, f"no user_id in register: {r.text}"
    return ({"Authorization": f"Bearer {tok}"}, uid)


async def test_leaderboard_public(ac):
    r = await ac.get("/social/leaderboard")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "items" in data and "period" in data


async def test_record_read_confers_xp_and_activity(ac):
    headers, uid = await _register_login(ac)
    # Record a read through the real endpoint with the JWT user.
    r = await ac.post(
        "/history",
        json={"source": "komiku", "content_id": "op", "content_type": "comic", "chapter_id": "1"},
        headers=headers,
    )
    assert r.status_code == 201, r.text

    r = await ac.get(f"/social/stats/{uid}")
    assert r.status_code == 200, r.text
    stats = r.json()["data"]
    assert stats["xp"] >= 10
    assert stats["chapters_read"] >= 1

    r = await ac.get("/social/activity")
    assert r.status_code == 200
    feed = r.json()["data"]["items"]
    assert any(e["user_id"] == uid and e["action"] == "read" for e in feed)


def test_level_curve():
    from app import gamification

    assert gamification.level_from_xp(0) == 1
    assert gamification.level_from_xp(50) == 1
    assert gamification.level_from_xp(100) == 2
    assert gamification.level_from_xp(299) >= 2
    assert gamification.level_from_xp(99999) > 5


async def test_club_crud_requires_jwt(ac):
    headers, uid = await _register_login(ac)
    r = await ac.post("/social/clubs", json={"name": "One Piece Fans"}, headers=headers)
    assert r.status_code in (200, 201), r.text
    cid = r.json()["data"]["id"]

    r = await ac.get("/social/clubs?q=One Piece")
    assert r.status_code == 200
    assert any(c["id"] == cid for c in r.json()["data"]["items"])

    r = await ac.post(f"/social/clubs/{cid}/posts", json={"content": "Best arc?"}, headers=headers)
    assert r.status_code in (200, 201), r.text

    r = await ac.get(f"/social/clubs/{cid}")
    assert r.status_code == 200
    assert len(r.json()["data"]["posts"]) >= 1

    # join/leave by a second user
    h2, _ = await _register_login(ac)
    r = await ac.post(f"/social/clubs/{cid}/join", headers=h2)
    assert r.status_code in (200, 201), r.text
    r = await ac.post(f"/social/clubs/{cid}/leave", headers=h2)
    assert r.status_code == 200


async def test_club_create_without_jwt_401(ac):
    r = await ac.post("/social/clubs", json={"name": "NoAuth Club"})
    assert r.status_code == 401
