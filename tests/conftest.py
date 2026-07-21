"""Shared test fixtures for SankaApi.

Tests run with OFFLINE_MODE=1 so sources read local fixtures (no network).
The rate-limiter's in-memory storage is reset between tests so one test's hits
do not bleed into another.
"""
from __future__ import annotations

import os

# Must be set before importing the app so Settings picks it up.
os.environ.setdefault("OFFLINE_MODE", "1")

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.ratelimit import limiter


@pytest.fixture(autouse=True)
def _reset_rate_limit_storage():
    """Clear slowapi's in-memory counters before each test.

    Without this, the cumulative request count from earlier tests would cause
    later tests to receive spurious 429s.
    """
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
