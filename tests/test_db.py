"""Tests for the SQLite database layer + /history endpoints.

We redirect the SQLAlchemy engine at a per-test SQLite file under
``tmp_path`` so each test runs against an isolated, empty database. The
global engine + session-factory cached in ``app.db`` are disposed and reset
between tests so a previous file/url does not leak through.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app import db as db_module


def _wire_tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> str:
    """Point the engine at ``tmp_path/test_history.sqlite`` and reset state."""
    url = f"sqlite+aiosqlite:///{tmp_path}/test_history.sqlite"
    monkeypatch.setenv("DATABASE_URL", url)
    db_module._engine = None  # noqa: SLF001 — drop cached engine
    db_module._session_factory = None  # noqa: SLF001
    return url


async def _fresh_client() -> AsyncClient:
    """Build an AsyncClient bound to the live ``app`` (lifespan runs init_db)."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# `app` is imported lazily so OFFLINE_MODE is set first by conftest.
from app.main import app  # noqa: E402


@pytest.fixture
async def tmp_db(monkeypatch, tmp_path):
    """Yield a DB URL pointed at a tmp_path file, with the engine reset.

    Also runs ``init_db`` so endpoints can be hit immediately. Tears the
    engine back down afterwards so the next test starts clean.
    """
    url = _wire_tmp_db(monkeypatch, tmp_path)
    await db_module.init_db()
    yield url
    await db_module.dispose_engine()
    db_module._engine = None  # noqa: SLF001
    db_module._session_factory = None  # noqa: SLF001


@pytest.mark.asyncio
async def test_post_history_creates_row(tmp_db):
    """POST /history returns the inserted row with a server-assigned id+read_at."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.post(
            "/history",
            json={
                "user_id": 1,
                "source": "otakudesu",
                "content_id": "boruto",
                "content_type": "anime",
                "chapter_id": "ep-1",
            },
        )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user_id"] == 1
    assert body["source"] == "otakudesu"
    assert body["content_id"] == "boruto"
    assert body["content_type"] == "anime"
    assert body["chapter_id"] == "ep-1"
    assert isinstance(body["id"], int) and body["id"] >= 1
    assert body["read_at"]  # ISO timestamp string, non-empty


@pytest.mark.asyncio
async def test_get_history_returns_rows_newest_first(tmp_db):
    """Two POSTs then a GET return both rows, newest first."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post(
            "/history",
            json={
                "user_id": 7,
                "source": "komiku",
                "content_id": "one-piece",
                "content_type": "comic",
                "chapter_id": "ch-1000",
            },
        )
        await client.post(
            "/history",
            json={
                "user_id": 7,
                "source": "sakuranovel",
                "content_id": "tensei",
                "content_type": "novel",
                "chapter_id": "ch-3",
            },
        )
        r = await client.get("/history", params={"user_id": 7})

    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 2
    # Newest first ordering
    assert rows[0]["read_at"] >= rows[1]["read_at"]
    contents = {(row["content_type"], row["content_id"]) for row in rows}
    assert contents == {("comic", "one-piece"), ("novel", "tensei")}


@pytest.mark.asyncio
async def test_get_history_filters_by_content_type(tmp_db):
    """The content_type query param narrows results to that medium."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        for ct in ("anime", "anime", "comic", "novel"):
            await client.post(
                "/history",
                json={
                    "user_id": 2,
                    "source": "otakudesu",
                    "content_id": f"x-{ct}",
                    "content_type": ct,
                    "chapter_id": "1",
                },
            )
        r = await client.get("/history", params={"user_id": 2, "content_type": "anime"})

    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    assert {row["content_type"] for row in rows} == {"anime"}


@pytest.mark.asyncio
async def test_get_history_requires_user_id(tmp_db):
    """GET /history without user_id (no JWT, no service key) returns 400."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/history")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_get_history_empty_for_unknown_user(tmp_db):
    """GET /history for an id with no rows returns [] (200), not 404."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/history", params={"user_id": 999})
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_post_history_validates_content_type(tmp_db):
    """content_type must be one of anime/comic/novel — else 422."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.post(
            "/history",
            json={
                "user_id": 1,
                "source": "otakudesu",
                "content_id": "boruto",
                "content_type": "podcast",  # not allowed
                "chapter_id": "ep-1",
            },
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_init_db_creates_file_and_tables(tmp_path, monkeypatch):
    """init_db on a tmp_path SQLite writes the file and creates both tables."""
    _wire_tmp_db(monkeypatch, tmp_path)
    target = tmp_path / "fresh.sqlite"
    assert not target.exists()

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{target}")
    db_module._engine = None  # noqa: SLF001
    await db_module.init_db()

    assert target.exists(), "SQLite file should be created by init_db"
    # Both model tables are registered with the declarative Base.
    assert set(db_module.Base.metadata.tables.keys()) >= {
        "users",
        "reading_history",
        "bookmarks",
        "webhook_subscriptions",
        "user_preferences",
    }

    await db_module.dispose_engine()
    db_module._engine = None  # noqa: SLF001
    db_module._session_factory = None  # noqa: SLF001
