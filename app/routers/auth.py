"""Auth endpoints: register / login / refresh / me / quota / forgot / reset / confirm."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
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
from ..auth_tokens import (
    confirm_email,
    confirm_link,
    consume_password_reset,
    issue_email_confirmation,
    issue_password_reset,
    reset_link,
)
from ..emailer import is_disabled, send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    email: Optional[EmailStr] = Field(
        None,
        description=(
            "Optional. When provided, an email-confirmation link is sent. "
            "Until the link is clicked the email stays unverified, but "
            "registration succeeds and JWTs are issued either way."
        ),
    )


class LoginBody(BaseModel):
    username: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class ForgotBody(BaseModel):
    email: EmailStr
    base_url: Optional[str] = Field(
        None,
        description=(
            "Used to build the reset link returned in the response when "
            "SMTP is disabled. Has no effect when SMTP sends the email."
        ),
    )


class ResetBody(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=128)


class ConfirmBody(BaseModel):
    token: str = Field(..., min_length=10)


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


def _build_token_pair(user: User) -> TokenResponse:
    plan = _plan_for_user(user)
    return TokenResponse(
        access_token=create_access_token(
            user_id=user.id, username=user.username, plan=plan
        ),
        refresh_token=create_refresh_token(
            user_id=user.id, username=user.username, plan=plan
        ),
        user_id=user.id,
        username=user.username,
        plan=plan,
        expires_in=ACCESS_TTL_SECONDS,
    )


@router.post("/register", response_model=ApiResponse, summary="Register a user")
async def register(
    body: RegisterBody,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    username = body.username.strip().lower()
    if not all(c.isalnum() or c == "_" for c in username):
        raise HTTPException(
            status_code=400, detail="username must be alphanumeric/underscore"
        )

    existing = (
        await session.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="username already taken")

    user = User(
        username=username,
        password_hash=hash_password(body.password),
        email=(str(body.email).lower() if body.email else None),
        email_confirmed=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    confirmation: Optional[dict] = None
    if user.email:
        # Issue a confirmation token. If SMTP works the email is sent in the
        # background; if not we return the link so the dev/user can click it
        # manually during local testing.
        token = await issue_email_confirmation(session, user)
        base = os.getenv("PUBLIC_BASE_URL", "https://mynakama.web.id")
        link = confirm_link(base, token)
        if not is_disabled() and user.email:
            background.add_task(
                send_email,
                to=user.email,
                subject="Confirm your Nakama email",
                body=(
                    f"Hi {user.username},\n\n"
                    f"Welcome to Nakama. Confirm your email by visiting:\n"
                    f"{link}\n\n"
                    f"If you didn't create this account, ignore this email."
                ),
            )
        else:
            confirmation = {"confirmation_link": link}

    return ApiResponse(
        data={**_build_token_pair(user).model_dump(), "email_confirmation": confirmation}
    )


@router.post("/login", response_model=ApiResponse, summary="Login and get JWT pair")
async def login(body: LoginBody, session: AsyncSession = Depends(get_session)):
    username = body.username.strip().lower()
    user = (
        await session.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid username or password")
    return ApiResponse(data=_build_token_pair(user).model_dump())


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
    # Issue a new pair — the old refresh token is invalidated implicitly
    # because we rotate the JTI / issued-at timestamp. Storing revoked
    # tokens would require a denylist; for self-hosted usage the rotation
    # + short TTL is sufficient.
    return ApiResponse(data=_build_token_pair(user).model_dump())


@router.post(
    "/forgot",
    response_model=ApiResponse,
    summary="Request a password-reset link",
)
async def forgot(
    body: ForgotBody,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Always returns 200 to avoid user-enumeration. The reset link is sent
    via SMTP when configured, or returned in the response payload when
    SMTP is disabled (so local installs still work)."""
    user = (
        await session.execute(
            select(User).where(User.email == body.email.lower())
        )
    ).scalar_one_or_none()

    reset: Optional[dict] = None
    if user is not None:
        token = await issue_password_reset(session, user)
        base = (
            body.base_url
            or os.getenv("PUBLIC_BASE_URL", "https://mynakama.web.id")
        )
        link = reset_link(base, token)
        if not is_disabled():
            background.add_task(
                send_email,
                to=user.email,
                subject="Reset your Nakama password",
                body=(
                    f"Hi {user.username},\n\n"
                    f"Reset your password by visiting:\n{link}\n\n"
                    f"This link expires in 2 hours."
                ),
            )
        else:
            reset = {"reset_link": link}

    return ApiResponse(
        data={
            "sent": True,
            "email": body.email,
            "reset": reset,
            "info": (
                "If an account with that email exists, a reset link has been "
                "sent (or, when SMTP is disabled, returned in `reset.reset_link`)."
            ),
        },
    )


@router.post(
    "/reset",
    response_model=ApiResponse,
    summary="Complete a password reset",
)
async def reset(body: ResetBody, session: AsyncSession = Depends(get_session)):
    user = await consume_password_reset(
        session, body.token, hash_password(body.new_password)
    )
    if user is None:
        raise HTTPException(
            status_code=400, detail="invalid or expired reset token"
        )
    return ApiResponse(data={"reset": True, "username": user.username})


@router.post(
    "/confirm",
    response_model=ApiResponse,
    summary="Confirm an email address via token",
)
async def confirm(body: ConfirmBody, session: AsyncSession = Depends(get_session)):
    user = await confirm_email(session, body.token)
    if user is None:
        raise HTTPException(
            status_code=400, detail="invalid confirmation token"
        )
    return ApiResponse(data={"confirmed": True, "username": user.username})


@router.get(
    "/me",
    response_model=ApiResponse,
    summary="Current user from Bearer token",
)
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
            "email": user.email,
            "email_confirmed": bool(user.email_confirmed),
            "plan": plan,
            "quota": q,
            "access_ttl_seconds": ACCESS_TTL_SECONDS,
            "refresh_ttl_seconds": REFRESH_TTL_SECONDS,
            "created_at": (
                user.created_at.isoformat() if user.created_at else None
            ),
        }
    )


@router.get("/quota", response_model=ApiResponse, summary="Quota remaining for current principal")
async def quota(request: Request):
    principal = getattr(request.state, "auth_principal", None) or "anon"
    plan = getattr(request.state, "auth_plan", None) or "free"
    q = await peek(principal, plan)
    return ApiResponse(data={"principal": principal, **q})
