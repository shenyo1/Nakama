"""Token generation helpers for password reset and email confirmation.

These are NOT JWTs — they're opaque, single-use tokens stored on the user
row. The flow is:

  - forgot password → POST /auth/forgot {email} → server generates a token,
    stores ``(token, expires_at)`` on the user row, and (optionally) sends
    an email containing a reset link with the token.
  - reset password → POST /auth/reset {token, new_password} → server looks
    up by token, verifies it's not expired, hashes the new password, clears
    the token.

Same pattern for email confirmation.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import User


# Reasonable expiry for one-time tokens. Long enough for the user to click
# the link in their inbox, short enough that a leaked token can't be used
# forever.
RESET_TOKEN_TTL = timedelta(hours=2)
CONFIRM_TOKEN_TTL = timedelta(days=3)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_naive(dt: datetime) -> datetime:
    """Normalize to naive UTC for comparison with SQLite-stored datetimes.

    The ``User.password_reset_expires_at`` column is stored as
    ``TIMESTAMP WITHOUT TIME ZONE`` on SQLite (the test DB) and as
    ``TIMESTAMP WITH TIME ZONE`` on Postgres. SQLite returns naive UTC;
    Postgres returns aware. To make ``_now() > expires`` consistent across
    both, we always compare in naive UTC.
    """
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def new_token() -> str:
    """Cryptographically secure URL-safe token (32 bytes ≈ 43 chars)."""
    return secrets.token_urlsafe(32)


async def issue_password_reset(session: AsyncSession, user: User) -> str:
    """Generate and persist a password-reset token. Returns the token."""
    token = new_token()
    user.password_reset_token = token
    # SQLite stores naive datetimes; strip tzinfo so comparisons work there.
    expires = _now() + RESET_TOKEN_TTL
    if expires.tzinfo is not None:
        expires = expires.replace(tzinfo=None)
    user.password_reset_expires_at = expires
    session.add(user)
    await session.commit()
    return token


async def consume_password_reset(
    session: AsyncSession, token: str, new_password_hash: str
) -> Optional[User]:
    """Look up a user by reset token, verify, hash new password, clear token.

    Returns the user on success, ``None`` on any failure (invalid token,
    expired, or user not found).
    """
    user = (
        await session.execute(
            select(User).where(User.password_reset_token == token)
        )
    ).scalar_one_or_none()
    if user is None:
        return None
    expires = user.password_reset_expires_at
    if expires is None:
        return None
    # Compare in naive UTC so SQLite + Postgres both work.
    if _as_naive(_now()) > _as_naive(expires):
        return None
    user.password_hash = new_password_hash
    user.password_reset_token = None
    user.password_reset_expires_at = None
    # Flush before commit so attributes stay attached to the instance and
    # callers can read them without triggering a post-commit lazy reload.
    await session.flush()
    # Snapshot the values we want callers to read.
    snapshot = {
        "id": user.id,
        "password_hash": user.password_hash,
        "password_reset_token": user.password_reset_token,
        "password_reset_expires_at": user.password_reset_expires_at,
    }
    await session.commit()
    # Re-fetch in a fresh state so attributes are bound and won't be expired.
    refreshed = (
        await session.execute(select(User).where(User.id == snapshot["id"]))
    ).scalar_one()
    # Stash the snapshot onto the instance for the caller.
    refreshed.password_hash = snapshot["password_hash"]
    refreshed.password_reset_token = snapshot["password_reset_token"]
    refreshed.password_reset_expires_at = snapshot["password_reset_expires_at"]
    return refreshed


async def issue_email_confirmation(session: AsyncSession, user: User) -> str:
    """Generate and persist an email-confirmation token. Returns the token."""
    token = new_token()
    user.email_confirm_token = token
    user.email_confirmed = False
    session.add(user)
    await session.commit()
    return token


async def confirm_email(session: AsyncSession, token: str) -> Optional[User]:
    """Look up user by email-confirm token and mark email_confirmed=True."""
    user = (
        await session.execute(
            select(User).where(User.email_confirm_token == token)
        )
    ).scalar_one_or_none()
    if user is None:
        return None
    user_id = user.id
    user.email_confirmed = True
    user.email_confirm_token = None
    await session.flush()
    confirmed_flag = user.email_confirmed
    token_after = user.email_confirm_token
    await session.commit()
    # Re-fetch in fresh state and re-stash values to avoid lazy reload.
    refreshed = (
        await session.execute(select(User).where(User.id == user_id))
    ).scalar_one()
    refreshed.email_confirmed = confirmed_flag
    refreshed.email_confirm_token = token_after
    return refreshed


def reset_link(base_url: str, token: str) -> str:
    return f"{base_url.rstrip('/')}/reset-password?token={token}"


def confirm_link(base_url: str, token: str) -> str:
    return f"{base_url.rstrip('/')}/confirm-email?token={token}"
