"""Nakama Originals — database models for original content platform.

Stores creator-uploaded original series (comics, novels) that are NOT
scraped from external sources. Includes a lightweight commission workflow:
creator uploads → admin approves → published.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

if TYPE_CHECKING:
    from .db import User


class OriginalSeries(Base):
    """A creator-uploaded original series (comic or novel)."""

    __tablename__ = "original_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # 'comic' | 'novel'
    synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    banner_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    author_name: Mapped[str] = mapped_column(String(128), nullable=False)
    author_bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    genres: Mapped[str | None] = mapped_column(String(512), nullable=True)  # comma-separated
    status: Mapped[str] = mapped_column(
        String(32), default="draft", nullable=False
    )  # draft | pending | published | rejected
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    commission_pct: Mapped[int] = mapped_column(Integer, default=70, nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    creator_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    chapters: Mapped[list["OriginalChapter"]] = relationship(
        back_populates="series", cascade="all, delete-orphan", order_by="OriginalChapter.chapter_number"
    )
    creator: Mapped[Optional["User"]] = relationship(back_populates="original_series")


class OriginalChapter(Base):
    """A single chapter of an original series."""

    __tablename__ = "original_chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("original_series.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)  # prose for novels
    image_urls: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array for comics
    status: Mapped[str] = mapped_column(
        String(32), default="draft", nullable=False
    )  # draft | published
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    series: Mapped["OriginalSeries"] = relationship(back_populates="chapters")


class CreatorApplication(Base):
    """Application from a user to become a Nakama Original creator."""

    __tablename__ = "creator_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    pen_name: Mapped[str] = mapped_column(String(128), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sample_work: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_types: Mapped[str] = mapped_column(String(64), nullable=False)  # comic,novel,both
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False
    )  # pending | approved | rejected
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
