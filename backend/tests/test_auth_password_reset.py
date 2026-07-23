"""Tests for v2.6.0 auth additions: email confirmation + password reset flow."""
from __future__ import annotations

import asyncio
import os
import pytest

# Force SMTP off so reset/confirmation links come back in the response.
os.environ["SMTP_DISABLED"] = "1"

from sqlalchemy import select

# Import after env var so it propagates
from app.auth_tokens import (
    confirm_email,
    consume_password_reset,
    issue_email_confirmation,
    issue_password_reset,
    new_token,
)
from app.db import User, get_engine, init_db, dispose_engine
from app.security import hash_password, verify_password
from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module", autouse=True)
async def _setup_db():
    """Init schema once for the whole module.

    For SQLite (used in tests) we drop and recreate the users table so the
    new ``email``, ``email_confirmed``, etc. columns exist. Postgres supports
    ``ALTER TABLE ... ADD COLUMN IF NOT EXISTS`` so production auto-migrates.
    """
    from app.db import Base
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text as sql_text

    engine = get_engine()
    db_url = os.getenv("DATABASE_URL", "")
    is_sqlite = "sqlite" in db_url.lower()

    if is_sqlite:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    else:
        # Production-style: create_all + forward columns
        await init_db()
    yield
    await dispose_engine()


async def _make_user(username: str = "authtest1", password: str = "supersecret123") -> int:
    """Insert a user and return its primary key. Clean any prior copy first."""
    from sqlalchemy import delete

    engine = get_engine()
    async with AsyncSession(engine) as s:
        await s.execute(delete(User).where(User.username == username))
        u = User(
            username=username,
            password_hash=hash_password(password),
            email=f"{username}@example.com",
        )
        s.add(u)
        await s.flush()
        user_id = u.id
        await s.commit()
        return user_id


async def test_token_helpers_basic():
    """Tokens are URL-safe and non-empty."""
    t1 = new_token()
    t2 = new_token()
    assert t1 and t2
    assert t1 != t2
    assert len(t1) >= 30


async def test_password_reset_round_trip():
    """Issue -> consume -> verify new password works, old fails."""
    user_id = await _make_user("authtest_reset", "oldpass123")
    engine = get_engine()

    # Session 1: issue the token
    async with AsyncSession(engine) as s1:
        s1_user = (
            await s1.execute(select(User).where(User.id == user_id))
        ).scalar_one()
        token = await issue_password_reset(s1, s1_user)
        assert token

    # Session 2: read fresh from DB, capture fields before session closes
    async with AsyncSession(engine) as s2:
        u = (
            await s2.execute(select(User).where(User.id == user_id))
        ).scalar_one()
        assert u.password_reset_token == token
        assert u.password_reset_expires_at is not None
        old_hash = u.password_hash

        updated = await consume_password_reset(s2, token, hash_password("newpass456"))
        # Capture all needed fields while session is still alive.
        assert updated is not None
        assert updated.id == user_id
        assert updated.password_reset_token is None
        assert updated.password_reset_expires_at is None
        new_hash = updated.password_hash

    assert verify_password("newpass456", new_hash)
    # Old password must not verify against the NEW hash (hash actually changed).
    assert not verify_password("oldpass123", new_hash)


async def test_password_reset_invalid_token():
    """Consuming a non-existent token returns None."""
    engine = get_engine()
    async with AsyncSession(engine) as s:
        result = await consume_password_reset(s, "definitely-not-a-real-token", hash_password("foo12345"))
        assert result is None


async def test_email_confirmation_round_trip():
    """Issue -> confirm -> email_confirmed flips to True."""
    user_id = await _make_user("authtest_confirm", "oldpass123")
    engine = get_engine()

    # Session 1: issue token
    async with AsyncSession(engine) as s1:
        s1_user = (
            await s1.execute(select(User).where(User.id == user_id))
        ).scalar_one()
        token = await issue_email_confirmation(s1, s1_user)
        assert token

    # Session 2: read fresh + confirm + capture fields
    async with AsyncSession(engine) as s2:
        u = (
            await s2.execute(select(User).where(User.id == user_id))
        ).scalar_one()
        assert u.email_confirm_token == token
        assert u.email_confirmed is False

        confirmed = await confirm_email(s2, token)
        assert confirmed is not None
        assert confirmed.id == user_id
        confirmed_flag = confirmed.email_confirmed
        token_after = confirmed.email_confirm_token

    assert confirmed_flag is True
    assert token_after is None


async def test_email_confirmation_invalid_token():
    engine = get_engine()
    async with AsyncSession(engine) as s:
        result = await confirm_email(s, "not-a-valid-token")
        assert result is None


async def test_register_endpoint_includes_confirmation_link_when_email_given():
    """With SMTP disabled, /register with email returns the confirmation link."""
    import httpx
    from app.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/auth/register",
            json={
                "username": "authtest_reg_email",
                "password": "supersecret123",
                "email": "authtest_reg_email@example.com",
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        assert "access_token" in body["data"]
        conf = body["data"].get("email_confirmation")
        assert conf and "confirmation_link" in conf
        # Confirm the link works
        link = conf["confirmation_link"]
        assert "token=" in link


async def test_register_endpoint_without_email_no_confirmation():
    """Plain username/password register still works (backward-compatible)."""
    import httpx
    from app.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/auth/register",
            json={"username": "authtest_reg_plain", "password": "supersecret123"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["data"]["email_confirmation"] is None


async def test_forgot_returns_reset_link_when_smtp_disabled():
    """POST /auth/forgot returns a reset link in the response when SMTP is off."""
    import httpx
    from app.main import app

    # Need a user with email
    await _make_user("authtest_forgot", "supersecret123")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/auth/forgot",
            json={"email": "authtest_forgot@example.com"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        assert body["data"]["sent"] is True
        # SMTP disabled -> reset link exposed
        assert body["data"]["reset"] and "reset_link" in body["data"]["reset"]


async def test_forgot_silent_on_unknown_email():
    """POST /auth/forgot never reveals whether the email exists."""
    import httpx
    from app.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/auth/forgot",
            json={"email": "ghost-no-such-user@example.com"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["data"]["sent"] is True
        assert body["data"]["reset"] is None  # No user = no link


async def test_reset_endpoint_round_trip():
    """End-to-end: forgot -> reset -> login with new password works."""
    import httpx
    from app.main import app

    await _make_user("authtest_full_flow", "supersecret123")

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. request reset
        r1 = await client.post(
            "/auth/forgot",
            json={"email": "authtest_full_flow@example.com"},
        )
        assert r1.status_code == 200
        reset_link = r1.json()["data"]["reset"]["reset_link"]
        # extract token from query string
        token = reset_link.split("token=")[1]

        # 2. perform reset
        r2 = await client.post(
            "/auth/reset",
            json={"token": token, "new_password": "brandnewpass456"},
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["data"]["reset"] is True

        # 3. login with new password works
        r3 = await client.post(
            "/auth/login",
            json={"username": "authtest_full_flow", "password": "brandnewpass456"},
        )
        assert r3.status_code == 200, r3.text
        assert "access_token" in r3.json()["data"]

        # 4. old password no longer works
        r4 = await client.post(
            "/auth/login",
            json={"username": "authtest_full_flow", "password": "supersecret123"},
        )
        assert r4.status_code == 401


async def test_reset_endpoint_rejects_garbage():
    """POST /auth/reset with bad token returns 400."""
    import httpx
    from app.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/auth/reset",
            json={"token": "garbage-token-no-such-thing", "new_password": "validnew123"},
        )
        assert resp.status_code == 400


async def test_refresh_token_returns_new_pair():
    """Refresh issues a new access + refresh token (rotation)."""
    import httpx
    from app.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Register first
        await client.post(
            "/auth/register",
            json={"username": "authtest_refresh", "password": "supersecret123"},
        )
        # Login
        r = await client.post(
            "/auth/login",
            json={"username": "authtest_refresh", "password": "supersecret123"},
        )
        refresh = r.json()["data"]["refresh_token"]

        # Refresh
        r2 = await client.post("/auth/refresh", json={"refresh_token": refresh})
        assert r2.status_code == 200, r2.text
        body = r2.json()["data"]
        assert body["access_token"]
        assert body["refresh_token"]
        # Tokens differ (rotation)
        assert body["refresh_token"] != refresh


async def test_me_endpoint_includes_email_fields():
    """GET /auth/me exposes email + email_confirmed when set."""
    import httpx
    from app.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/auth/register",
            json={
                "username": "authtest_me",
                "password": "supersecret123",
                "email": "authtest_me@example.com",
            },
        )
        r = await client.post(
            "/auth/login",
            json={"username": "authtest_me", "password": "supersecret123"},
        )
        token = r.json()["data"]["access_token"]
        r2 = await client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert r2.status_code == 200, r2.text
        body = r2.json()["data"]
        assert body["email"] == "authtest_me@example.com"
        assert body["email_confirmed"] is False  # we never confirmed
        assert "created_at" in body
