"""Async SQLAlchemy database layer for NakamaApi.

Provides:

* An async engine + session factory bound to a configurable URL (default
  SQLite at ``./nakamadb.sqlite``, overridable via the ``DATABASE_URL`` env
  var so the same code path supports PostgreSQL in production).
* Two ORM models — ``User`` (placeholder for future auth) and
  ``ReadingHistory`` (per-user "I read this chapter" log).
* A ``get_session`` FastAPI dependency yielding an ``AsyncSession`` per
  request, plus ``init_db()`` to create all tables on startup.

Why a SQLite default?
---------------------
SQLite is ideal for the bundled single-binary / dev experience: zero
external services, fast, and the file lives next to the app. The same
SQLAlchemy models work against PostgreSQL/MySQL — just set
``DATABASE_URL=postgresql+asyncpg://user:pass@host/db`` and the engine
switches transparently.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import AsyncIterator

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _default_sqlite_url() -> str:
    """Build the default SQLite URL anchored at the project root.

    ``./nakamadb.sqlite`` is resolved against the current working directory so
    the file lands next to wherever the app is launched (dev mode, uvicorn,
    test runner, etc.).
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_root, "nakamadb.sqlite")
    return f"sqlite+aiosqlite:///{db_path}"


def get_database_url() -> str:
    """Resolve the active database URL.

    Order:
    1. ``DATABASE_URL`` environment variable (any async-driver URL).
    2. Fallback: ``sqlite+aiosqlite:///./nakamadb.sqlite``.
    """
    return os.getenv("DATABASE_URL") or _default_sqlite_url()


# ---------------------------------------------------------------------------
# Declarative base + models
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class User(Base):
    """Application user. Placeholder for future authentication.

    ``password_hash`` carries the bcrypt/argon2 hash (never the plaintext).
    ``created_at`` is server-side default-Now for stable ordering.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    history: Mapped[list["ReadingHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ReadingHistory(Base):
    """A single "user X read chapter Y of content Z" event.

    ``content_type`` is a free-form string constrained to ``anime``,
    ``comic``, or ``novel`` at the API boundary. ``read_at`` is set by the
    server on insert so clients cannot forge timestamps.
    """

    __tablename__ = "reading_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    content_id: Mapped[str] = mapped_column(String(128), nullable=False)
    content_type: Mapped[str] = mapped_column(String(16), nullable=False)
    chapter_id: Mapped[str] = mapped_column(String(128), nullable=False)
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="history")


# ---------------------------------------------------------------------------
# Engine + session factory
# ---------------------------------------------------------------------------

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the lazily-initialised async engine, building it on first use.

    SQLite needs ``check_same_thread=False`` because the async driver hops
    between asyncio tasks. Other drivers (asyncpg, aiomysql) ignore the
    kwarg so it is safe to pass unconditionally.
    """
    global _engine
    if _engine is None:
        url = get_database_url()
        connect_args: dict = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_async_engine(url, echo=False, connect_args=connect_args)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory, creating one on first use."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _session_factory


async def init_db() -> None:
    """Create all tables. Called from the FastAPI lifespan on startup.

    Safe to call repeatedly: ``create_all`` is a no-op for tables that
    already exist with the same shape.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Tear down the engine. Called from the FastAPI lifespan on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped ``AsyncSession``.

    The session is closed when the request finishes; commit/rollback is
    the caller's responsibility (endpoints call ``session.commit()``
    explicitly after mutations).
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session
