"""Password hashing + JWT helpers for Nakama auth (Tier 4)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from typing import Any, Dict, Optional

import jwt

from .config import get_settings

_ALGO = "HS256"
_ACCESS_TTL = 15 * 60  # 15 minutes
_REFRESH_TTL = 7 * 24 * 3600  # 7 days


def hash_password(password: str) -> str:
    """Return a scrypt password hash (stdlib, no bcrypt dep)."""
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.urlsafe_b64encode(salt + dk).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        if not password_hash.startswith("scrypt$"):
            return False
        raw = base64.urlsafe_b64decode(password_hash[len("scrypt$") :].encode("ascii"))
        salt, expected = raw[:16], raw[16:]
        dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def _secret() -> str:
    s = get_settings()
    secret = getattr(s, "jwt_secret", None) or s.api_key
    if not secret:
        # Dev/test fallback — never use in production without JWT_SECRET/API_KEY.
        secret = "nakama-dev-insecure-secret"
    return secret


def create_access_token(*, user_id: int, username: str, plan: str = "free") -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "username": username,
        "plan": plan,
        "type": "access",
        "iat": now,
        "exp": now + _ACCESS_TTL,
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGO)


def create_refresh_token(*, user_id: int, username: str, plan: str = "free") -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "username": username,
        "plan": plan,
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
        "iat": now,
        "exp": now + _REFRESH_TTL,
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGO)


def decode_token(token: str, *, expected_type: Optional[str] = "access") -> Dict[str, Any]:
    data = jwt.decode(token, _secret(), algorithms=[_ALGO])
    if expected_type and data.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"expected token type {expected_type}")
    return data


ACCESS_TTL_SECONDS = _ACCESS_TTL
REFRESH_TTL_SECONDS = _REFRESH_TTL


# ---------------------------------------------------------------------------
# Refresh-token revocation (JTI denylist)
# ---------------------------------------------------------------------------
# Backed by Redis so it survives restarts. Key: ``revoked_jti:<jti>`` with TTL
# equal to the refresh-token's remaining lifetime so the entry self-cleans.
# All operations are async — call from an async endpoint context.

async def revoke_refresh_token(token: str) -> bool:
    """Add the JTI of ``token`` to the denylist. Returns False if invalid.

    Safe to call with malformed/expired tokens (returns False silently).
    """
    try:
        data = decode_token(token, expected_type="refresh")
    except Exception:
        return False
    jti = data.get("jti")
    if not jti:
        return False
    exp = int(data.get("exp", 0))
    remaining = max(1, exp - int(time.time()))
    try:
        from app.cache import get_redis  # type: ignore

        r = get_redis()
        if r is None:
            return False
        await r.setex(f"revoked_jti:{jti}", remaining, "1")
        return True
    except Exception:
        return False


async def is_refresh_revoked(token: str) -> bool:
    """Check whether ``token``'s JTI has been revoked."""
    try:
        data = decode_token(token, expected_type="refresh")
    except Exception:
        return False
    jti = data.get("jti")
    if not jti:
        return False
    try:
        from app.cache import get_redis  # type: ignore

        r = get_redis()
        if r is None:
            return False
        return bool(await r.exists(f"revoked_jti:{jti}"))
    except Exception:
        return False
