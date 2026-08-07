"""Gamification & social models — Fase 4 (learnings from Sanka/Lovable).

Adds XP / reading-streak / weekly leaderboard / activity feed / reading clubs
on top of the existing ``ReadingHistory`` log. Every read event already lands
in ``reading_history``; these models aggregate and reward it.

Patterns adopted from Sanka:
  * ``get_weekly_leaderboard`` — XP + streak + chapters_week ranking
  * ``activity_feed`` — join of read/rate/comment/follow/bookmark actions
  * reading clubs (create/join/leave/posts) with realtime-ready member counts
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    func,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class UserStats(Base):
    """Durable per-user gamification counters (aggregated from events)."""

    __tablename__ = "user_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    chapters_read: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # YYYY-MM-DD of the last day with at least one read event.
    last_read_day: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    reading_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship()

class ActivityEvent(Base):  # noqa: E701 - forward-ref kept string like community_models
    """Social activity feed entry (read/rate/comment/list/follow/bookmark)."""

    __tablename__ = "activity_events"
    __table_args__ = (
        Index("ix_activity_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(24), nullable=False
    )  # read|rate|comment|list|follow|bookmark|create_club|join_club
    content_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # anime|comic|novel|creator
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    content_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ref_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # e.g. followed user
    payload: Mapped[Optional[dict]] = mapped_column(__import__("sqlalchemy").JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReadingClub(Base):
    """A user-created reading club (per-series or general)."""

    __tablename__ = "reading_clubs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    content_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # anime|comic|novel
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    content_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship()


class ReadingClubMember(Base):
    __tablename__ = "reading_club_members"
    __table_args__ = (
        UniqueConstraint("club_id", "user_id", name="uq_club_member"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    club_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reading_clubs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), default="member", nullable=False)  # owner|member
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReadingClubPost(Base):
    __tablename__ = "reading_club_posts"
    __table_args__ = (
        Index("ix_club_posts_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    club_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reading_clubs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
