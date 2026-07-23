"""User preferences router — persistent per-user UI/UX settings.

GET /preferences              — read current user's preferences
PUT /preferences              — replace current user's preferences
PATCH /preferences            — merge partial update into preferences
DELETE /preferences           — reset to defaults

Requires JWT auth (Authorization: Bearer <token>). Each user has exactly one
preferences row keyed by ``key="default"``; the JSON payload is opaque to the
server so clients can evolve their UI without API changes.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import User, UserPreference, get_session
from ..dependencies import current_user_required

router = APIRouter(prefix="/preferences", tags=["preferences"])


class PreferencesIn(BaseModel):
    payload: Dict[str, Any] = Field(default_factory=dict)


class PreferencesOut(BaseModel):
    payload: Dict[str, Any]
    updated_at: Optional[str] = None


async def _get_or_create_pref(session: AsyncSession, user_id: int) -> UserPreference:
    """Fetch the user's default prefs row, creating an empty one if missing."""
    result = await session.execute(
        select(UserPreference)
        .where(UserPreference.user_id == user_id, UserPreference.key == "default")
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        pref = UserPreference(user_id=user_id, key="default", payload={})
        session.add(pref)
        await session.flush()
    return pref


@router.get("", response_model=PreferencesOut, summary="Get current user preferences")
async def get_preferences(
    request: Request,
    user: User = Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
) -> PreferencesOut:
    pref = await _get_or_create_pref(session, user.id)
    await session.commit()
    return PreferencesOut(
        payload=pref.payload or {},
        updated_at=pref.updated_at.isoformat() if pref.updated_at else None,
    )


@router.put("", response_model=PreferencesOut, summary="Replace current user preferences")
async def put_preferences(
    body: PreferencesIn,
    request: Request,
    user: User = Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
) -> PreferencesOut:
    pref = await _get_or_create_pref(session, user.id)
    pref.payload = body.payload
    # Touch updated_at while session is open to avoid lazy load after commit.
    updated_at = pref.updated_at
    await session.commit()
    return PreferencesOut(
        payload=pref.payload,
        updated_at=updated_at.isoformat() if updated_at else None,
    )


@router.patch("", response_model=PreferencesOut, summary="Merge partial update into preferences")
async def patch_preferences(
    body: PreferencesIn,
    request: Request,
    user: User = Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
) -> PreferencesOut:
    pref = await _get_or_create_pref(session, user.id)
    merged = {**(pref.payload or {}), **body.payload}
    pref.payload = merged
    updated_at = pref.updated_at
    await session.commit()
    return PreferencesOut(
        payload=pref.payload,
        updated_at=updated_at.isoformat() if updated_at else None,
    )


@router.delete("", response_model=PreferencesOut, summary="Reset preferences to defaults")
async def delete_preferences(
    request: Request,
    user: User = Depends(current_user_required),
    session: AsyncSession = Depends(get_session),
) -> PreferencesOut:
    pref = await _get_or_create_pref(session, user.id)
    pref.payload = {}
    updated_at = pref.updated_at
    await session.commit()
    return PreferencesOut(payload={}, updated_at=updated_at.isoformat() if updated_at else None)