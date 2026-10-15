"""
backend/app/core/security.py
─────────────────────────────
JWT token creation / verification and bcrypt password hashing.

All cryptographic operations are centralised here so that the rest of
the application never touches raw secrets or hashing logic directly.

Usage:
    from app.core.security import hash_password, verify_password, create_access_token

    hashed = hash_password("mysecret")
    ok     = verify_password("mysecret", hashed)    # → True

    token  = create_access_token({"sub": "42", "email": "a@b.com"})
    data   = decode_access_token(token)             # → {"sub": "42", …}
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────
# passlib wraps bcrypt; schemes list makes it easy to add future algorithms.
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Parameters
    ----------
    plain : str
        The user's raw password (never stored).

    Returns
    -------
    str
        A bcrypt hash string safe to store in the database.
    """
    _validate_bcrypt_password(plain)
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Parameters
    ----------
    plain  : The raw password the user provided.
    hashed : The hash stored in the database.

    Returns
    -------
    bool : True if the password matches, False otherwise.
    """
    _validate_bcrypt_password(plain)
    return _pwd_ctx.verify(plain, hashed)


def _validate_bcrypt_password(password: str) -> None:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Parameters
    ----------
    data          : Payload data (must include "sub" = user ID as str).
    expires_delta : Token lifetime. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns
    -------
    str : Encoded JWT string.

    Example
    -------
    token = create_access_token({"sub": "7", "email": "raj@corp.com"})
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload["exp"] = expire
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT access token.

    Parameters
    ----------
    token : The raw JWT string from the Authorization header.

    Returns
    -------
    dict : Decoded payload.

    Raises
    ------
    JWTError : If the token is invalid, expired, or tampered with.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "JWTError",
]
