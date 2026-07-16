"""
Security helpers: password hashing (bcrypt), JWT tokens (PyJWT), and
symmetric encryption for per-user secrets (Fernet).

The Fernet key is derived from JWT_SECRET so there's no extra env var to
manage in dev. In production, set a strong JWT_SECRET (rotating it will
invalidate stored encrypted Hub keys — users would re-enter them).
"""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

from app.core.config import settings, FEATURE_PERMISSIONS


# --- Passwords ---------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JWT ---------------------------------------------------------------------
def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Returns the payload, or raises jwt.PyJWTError on invalid/expired tokens."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


# --- Field encryption (Fernet) ----------------------------------------------
def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str | None:
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


# --- Feature Gating by Profile Type -----------------------------------------------
def require_feature(feature_name: str) -> Callable:
    """
    Decorator to gate endpoint access by user profile_type and available features.

    Usage:
        @router.get("/leads")
        @require_feature("lead_gen")
        async def list_leads(...):
            ...

    Checks if the current user's profile_type has access to the requested feature.
    Admins (is_staff or is_superuser) bypass all checks.
    Returns 403 Forbidden if feature is not available for the user's profile.

    Args:
        feature_name: The feature key to check (e.g., "lead_gen", "whatsapp_agent")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract the current user from kwargs (passed via FastAPI dependency injection)
            current_user = kwargs.get("current")
            if not current_user:
                # Try alternate naming patterns
                for key in kwargs:
                    obj = kwargs[key]
                    if hasattr(obj, "profile_type") and hasattr(obj, "email"):
                        current_user = obj
                        break

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # Admins (superuser or staff) bypass all feature checks
            if getattr(current_user, "is_staff", False) or getattr(current_user, "is_superuser", False):
                return await func(*args, **kwargs)

            # Check if user's profile_type has access to this feature
            profile_type = getattr(current_user, "profile_type", None)
            if not profile_type:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Profile type not set. Please complete your onboarding.",
                )

            allowed_features = FEATURE_PERMISSIONS.get(profile_type, set())
            if feature_name not in allowed_features:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This feature is not available for your account type. "
                           f"Profile: {profile_type}. Feature: {feature_name}.",
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator
