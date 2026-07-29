"""
Community feature SQLAlchemy models for Nakama.

Provides ORM models for:
- Review: user reviews on content (anime/comic/novel)
- Comment: threaded comments on content
- ReadingList: user-curated reading lists
- ReadingListItem: items within a reading list
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
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


class Review(Base):
    """A user review of content (anime/comic/novel).

    Each user can leave at most one review per (source, slug, kind) tuple.
    Rating is clamped to 1-5 at the application layer.
    """

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "source", "slug", "kind",
            name="uq_review_user_item",
        ),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating"),
        Index("ix_reviews_source_slug_kind", "source", "slug", "kind"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str] = mapped_column(String(256), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # anime|comic|novel
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="reviews")


class Comment(Base):
    """A threaded comment on content.

    ``parent_id`` enables nested replies (one level deep recommended).
    Top-level comments have ``parent_id IS NULL``.
    """

    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_source_slug_kind", "source", "slug", "kind"),
        Index("ix_comments_parent", "parent_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str] = mapped_column(String(256), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # anime|comic|novel
    body: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="comments", foreign_keys=[user_id])
    parent: Mapped[Optional["Comment"]] = relationship(
        "Comment", remote_side="Comment.id", back_populates="replies"
    )
    replies: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="parent", cascade="all, delete-orphan"
    )


class ReadingList(Base):
    """A user-curated reading list (public or private)."""

    __tablename__ = "reading_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="reading_lists")
    items: Mapped[list["ReadingListItem"]] = relationship(
        back_populates="list", cascade="all, delete-orphan"
    )


class ReadingListItem(Base):
    """An item within a reading list."""

    __tablename__ = "reading_list_items"
    __table_args__ = (
        UniqueConstraint(
            "list_id", "source", "slug", "kind",
            name="uq_list_item",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    list_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reading_lists.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str] = mapped_column(String(256), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # anime|comic|novel
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    list: Mapped["ReadingList"] = relationship(back_populates="items")
