"""Auth endpoints: register / login / refresh / me / quota."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import User, get_session
from ..quota import peek, quota_for_plan
from ..schemas import ApiResponse
from ..security import (
    ACCESS_TTL_SECONDS,
    REFRESH_TTL_SECONDS,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)


class LoginBody(BaseModel):
    username: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TTL_SECONDS
    user_id: int
    username: str
    plan: str = "free"


def _plan_for_user(user: User) -> str:
    # Future: store plan on user row. Default free for now.
    return getattr(user, "plan", None) or "free"


@router.post("/register", response_model=ApiResponse, summary="Register a user")
async def register(body: RegisterBody, session: AsyncSession = Depends(get_session)):
    username = body.username.strip().lower()
    if not username.isalnum() and "_" not in username:
        # allow alnum + underscore
        if not all(c.isalnum() or c == "_" for c in username):
            raise HTTPException(status_code=400, detail="username must be alphanumeric/underscore")
    existing = (
        await session.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="username already taken")
    user = User(username=username, password_hash=hash_password(body.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    plan = _plan_for_user(user)
    access = create_access_token(user_id=user.id, username=user.username, plan=plan)
    refresh = create_refresh_token(user_id=user.id, username=user.username, plan=plan)
    return ApiResponse(
        data=TokenResponse(
            access_token=access,
            refresh_token=refresh,
            user_id=user.id,
            username=user.username,
            plan=plan,
            expires_in=ACCESS_TTL_SECONDS,
        ).model_dump()
    )


@router.post("/login", response_model=ApiResponse, summary="Login and get JWT pair")
async def login(body: LoginBody, session: AsyncSession = Depends(get_session)):
    username = body.username.strip().lower()
    user = (
        await session.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid username or password")
    plan = _plan_for_user(user)
    access = create_access_token(user_id=user.id, username=user.username, plan=plan)
    refresh = create_refresh_token(user_id=user.id, username=user.username, plan=plan)
    return ApiResponse(
        data=TokenResponse(
            access_token=access,
            refresh_token=refresh,
            user_id=user.id,
            username=user.username,
            plan=plan,
            expires_in=ACCESS_TTL_SECONDS,
        ).model_dump()
    )


@router.post("/refresh", response_model=ApiResponse, summary="Refresh access token")
async def refresh(body: RefreshBody, session: AsyncSession = Depends(get_session)):
    try:
        data = decode_token(body.refresh_token, expected_type="refresh")
    except Exception:
        raise HTTPException(status_code=401, detail="invalid refresh token")
    user_id = int(data["sub"])
    user = (
        await session.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    plan = _plan_for_user(user)
    access = create_access_token(user_id=user.id, username=user.username, plan=plan)
    # rotate refresh
    refresh_tok = create_refresh_token(user_id=user.id, username=user.username, plan=plan)
    return ApiResponse(
        data=TokenResponse(
            access_token=access,
            refresh_token=refresh_tok,
            user_id=user.id,
            username=user.username,
            plan=plan,
            expires_in=ACCESS_TTL_SECONDS,
        ).model_dump()
    )


@router.get("/me", response_model=ApiResponse, summary="Current user from Bearer token")
async def me(request: Request, session: AsyncSession = Depends(get_session)):
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
    plan = data.get("plan") or _plan_for_user(user)
    q = await peek(f"user:{user.id}", plan)
    return ApiResponse(
        data={
            "user_id": user.id,
            "username": user.username,
            "plan": plan,
            "quota": q,
            "access_ttl_seconds": ACCESS_TTL_SECONDS,
            "refresh_ttl_seconds": REFRESH_TTL_SECONDS,
        }
    )


@router.get("/quota", response_model=ApiResponse, summary="Quota remaining for current principal")
async def quota(request: Request):
    principal = getattr(request.state, "auth_principal", None) or "anon"
    plan = getattr(request.state, "auth_plan", None) or "free"
    q = await peek(principal, plan)
    return ApiResponse(data={"principal": principal, **q})
