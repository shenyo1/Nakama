"""Reusable auth dependencies for routers that require a logged-in user.

JWT-only: bypasses the API-key middleware (those use ``request.state.auth_*``).
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import User, get_session
from .security import decode_token


async def current_user_required(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    """Resolve the current user from Authorization: Bearer <access_token>.

    Raises 401 on missing/invalid token or unknown user.
    """
    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    try:
        data = decode_token(token, expected_type="access")
    except Exception:
        raise HTTPException(status_code=401, detail="invalid access token")
    user_id = int(data["sub"])
    user = (
        await session.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    return user