"""Shared test fixtures for Nakama.

Tests run with OFFLINE_MODE=1 so sources read local fixtures (no network).
The rate-limiter's in-memory storage is reset between tests so one test's hits
do not bleed into another.
"""
from __future__ import annotations

import os

# Must be set before importing the app so Settings picks it up.
os.environ.setdefault("OFFLINE_MODE", "1")
# Tests default to open access unless a fixture explicitly enables API_KEY.
# Production .env must not leak into the pytest process.
os.environ.pop("API_KEY", None)
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-please-change-32b")
# Force SQLite for tests so auth/history don't hit production Postgres.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:////tmp/nakama-test.sqlite"

import asyncio as _asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.db import dispose_engine, init_db
from app.ratelimit import limiter

get_settings.cache_clear()


# Ensure the test DB has tables before tests run.
def _init_test_db() -> None:
    try:
        loop = _asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
        loop.run_until_complete(init_db())
    except RuntimeError:
        _asyncio.run(init_db())


_init_test_db()


@pytest.fixture(autouse=True)
def _reset_rate_limit_storage():
    """Clear slowapi's in-memory counters before each test."""
    storage = limiter._storage
    if storage is not None and hasattr(storage, "reset"):
        storage.reset()
    yield
    if storage is not None and hasattr(storage, "reset"):
        storage.reset()


@pytest.fixture
def api_key_enabled():
    """Enable API key auth for the duration of the test, then disable it."""
    s = get_settings()
    original = s.api_key
    s.api_key = "test-secret-key-123"
    yield s.api_key
    s.api_key = original


@pytest.fixture
async def client():
    """ASGI test client (no real network socket)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# Imported here (after env setup) so tests/test_*.py can do `from conftest import app`.
from app.main import app  # noqa: E402
