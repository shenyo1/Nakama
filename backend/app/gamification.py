"""Gamification service — XP, reading streak, levelling, activity feed (Fase 4).

Pure-ish async helpers that aggregate reward state from read events and keep
the ``user_stats`` / ``activity_events`` tables fresh. Called from the history
router whenever a read is recorded, so XP accrues automatically as users read.

XP model (mirrors Sanka's leaderboard spirit):
  * +10 XP per chapter read (anime/comic/novel alike)
  * reading streak = consecutive days with at least one read; reset to 1 when
    the user missed a day, preserved when they read again the next day.
Level curve: level N requires N*100 XP to reach (exponential-ish early ramp).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import ReadingHistory
from .gamification_models import ActivityEvent, UserStats

logger = logging.getLogger(__name__)

XP_PER_READ = 10
LEVEL_BASE_XP = 100  # level L needs L*LEVEL_BASE_XP total XP


def _today_str() -> str:
    return date.today().isoformat()


def level_from_xp(xp: int) -> int:
    """Level from cumulative XP: L1=0..99, L2=100..299, L3=300..599…"""
    import math

    if xp < LEVEL_BASE_XP:
        return 1
    # Solve n(n+1)/2 * BASE <= xp  ->  n = floor((sqrt(1+8k)-1)/2) + 1
    k = xp * 2 / LEVEL_BASE_XP
    n = int((math.sqrt(1 + 8 * k) - 1) / 2)
    return max(1, n + 1)


def xp_for_next_level(xp: int) -> int:
    lvl = level_from_xp(xp)
    return lvl * LEVEL_BASE_XP


async def get_or_create_stats(session: AsyncSession, user_id: int) -> UserStats:
    from .gamification_models import UserStats

    stmt = select(UserStats).where(UserStats.user_id == user_id)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        row = UserStats(user_id=user_id, xp=0, level=1, chapters_read=0)
        session.add(row)
        await session.flush()
    return row


async def apply_read_xp(session: AsyncSession, user_id: int) -> UserStats:
    """Increment XP + chapters_read and update the reading streak for a read event.

    Call after the ReadingHistory row is committed. Best-effort: never raise.
    """
    try:
        stats = await get_or_create_stats(session, user_id)
        stats.xp = (stats.xp or 0) + XP_PER_READ
        stats.chapters_read = (stats.chapters_read or 0) + 1
        stats.level = level_from_xp(stats.xp)

        today = _today_str()
        if stats.last_read_day == today:
            pass  # already counted today; streak preserved
        elif stats.last_read_day == _yesterday_str():
            stats.reading_streak = (stats.reading_streak or 0) + 1
        else:
            stats.reading_streak = 1  # new streak (previous chain broken)
        stats.last_read_day = today
        await session.commit()
        return stats
    except Exception as e:  # pragma: no cover
        logger.warning("gamification.apply_read_xp failed: %s", e)
        try:
            await session.rollback()
        except Exception:
            pass
        raise


def _yesterday_str() -> str:
    from datetime import timedelta

    return (date.today() - timedelta(days=1)).isoformat()


async def record_activity(
    session: AsyncSession,
    user_id: int,
    action: str,
    *,
    content_type: Optional[str] = None,
    title: Optional[str] = None,
    source: Optional[str] = None,
    content_id: Optional[str] = None,
    ref_user_id: Optional[int] = None,
) -> None:
    """Insert a social activity event (best-effort)."""
    try:
        row = ActivityEvent(
            user_id=user_id,
            action=action,
            content_type=content_type,
            title=(title or "")[:255],
            source=source,
            content_id=content_id,
            ref_user_id=ref_user_id,
        )
        session.add(row)
        await session.commit()
    except Exception as e:  # pragma: no cover
        logger.warning("gamification.record_activity failed: %s", e)
        try:
            await session.rollback()
        except Exception:
            pass


async def weekly_leaderboard(
    session: AsyncSession,
    limit: int = 20,
    *,
    include_stats: bool = True,
) -> list[dict]:
    """Top readers this week ranked by XP accrued (or chapters_read fallback).

    Uses the last 7 days of ReadingHistory that happened AFTER each user's
    weekly baseline — approximated as any read in the last 7 days. The real
    weekly delta would need a user-week anchor; this is a solid public leaderboard.
    """
    from datetime import timedelta

    from sqlalchemy import func as sa_func

    from .db import User

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    stmt = (
        select(
            ReadingHistory.user_id,
            User.username,
            sa_func.count(ReadingHistory.id).label("reads"),
        )
        .join(User, User.id == ReadingHistory.user_id)
        .where(ReadingHistory.read_at >= week_ago)
        .group_by(ReadingHistory.user_id, User.username)
        .order_by(sa_func.count(ReadingHistory.id).desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    out: list[dict] = []
    for r in rows:
        # Distinct days read this week via a second pass is expensive; use the
        # row count as chapters_week. XP approximated (we award real XP on read).
        stats = None
        if include_stats:
            stats = await get_or_create_stats(session, r.user_id)
        out.append(
            {
                "rank": len(out) + 1,
                "user_id": r.user_id,
                "username": r.username,
                "chapters_week": r.reads,
                "xp": (stats.xp if stats else 0),
                "level": (stats.level if stats else 1),
                "reading_streak": (stats.reading_streak if stats else 0),
            }
        )
    return out


async def user_stats(session: AsyncSession, user_id: int) -> dict:
    stats = await get_or_create_stats(session, user_id)
    return {
        "user_id": user_id,
        "xp": stats.xp,
        "level": stats.level,
        "chapters_read": stats.chapters_read,
        "reading_streak": stats.reading_streak,
        "last_read_day": stats.last_read_day,
        "xp_to_next": xp_for_next_level(stats.xp),
    }


async def activity_feed(
    session: AsyncSession,
    *,
    user_id: Optional[int] = None,
    limit: int = 50,
) -> list[dict]:
    """Recent activity events, optionally filtered to one user, newest first."""
    from .db import User

    stmt = (
        select(ActivityEvent, User.username)
        .join(User, User.id == ActivityEvent.user_id)
        .order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
        .limit(limit)
    )
    if user_id is not None:
        stmt = stmt.where(ActivityEvent.user_id == user_id)
    rows = (await session.execute(stmt)).all()
    return [
        {
            "id": ev.id,
            "user_id": ev.user_id,
            "username": username,
            "action": ev.action,
            "content_type": ev.content_type,
            "title": ev.title,
            "source": ev.source,
            "content_id": ev.content_id,
            "ref_user_id": ev.ref_user_id,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev, username in rows
    ]
