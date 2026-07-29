"""
Creator feature SQLAlchemy models for Nakama Tier 3.2.

Provides ORM models for:
- CreatorProfile: creator bio, social links, verification status
- CreatorSeries: a series/book/comic the creator publishes
- CreatorChapter: individual chapter content within a series
"""

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
    Index,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class CreatorProfile(Base):
    """Public-facing creator profile.

    One user = one creator profile. Contains display name, bio, social links,
    verification status, and follower count (denormalized for fast reads).
    """

    __tablename__ = "creator_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, index=True, nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    social_links: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # Denormalized counters for dashboard speed
    follower_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Verification / moderation
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="creator_profile")
    series: Mapped[list["CreatorSeries"]] = relationship(
        back_populates="creator", cascade="all, delete-orphan"
    )


class CreatorSeries(Base):
    """A series/book/comic published by a creator.

    Each series belongs to one creator. kind = 'novel'|'comic'|'art'.
    """

    __tablename__ = "creator_series"
    __table_args__ = (
        Index("ix_creator_series_creator_kind", "creator_id", "kind"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    creator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # novel|comic|art
    cover_image: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="ongoing", nullable=False,
    )  # ongoing|completed|hiatus
    # Denormalized counters
    chapter_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    creator: Mapped["CreatorProfile"] = relationship(back_populates="series")
    chapters: Mapped[list["CreatorChapter"]] = relationship(
        back_populates="series", cascade="all, delete-orphan",
        order_by="CreatorChapter.chapter_number",
    )


class CreatorChapter(Base):
    """Individual chapter within a creator's series.

    Content is stored as raw markdown/HTML. Chapter numbers are unique within
    a series (enforced at app layer since SQLite has limited unique constraints).
    """

    __tablename__ = "creator_chapters"
    __table_args__ = (
        Index("ix_creator_chapters_series_number", "series_id", "chapter_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("creator_series.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # markdown or HTML
    content_format: Mapped[str] = mapped_column(
        String(16), default="markdown", nullable=False,
    )  # markdown|html
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    series: Mapped["CreatorSeries"] = relationship(back_populates="chapters")


class CreatorFollower(Base):
    """Many-to-many join: user follows a creator."""

    __tablename__ = "creator_followers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    creator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# Back-populate User with creator_profile relationship
from .db import User
User.creator_profile = relationship(
    "CreatorProfile", back_populates="user", uselist=False,
    cascade="all, delete-orphan",
)
