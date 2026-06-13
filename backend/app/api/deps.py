"""Shared FastAPI dependencies (current user, etc.)."""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise _credentials_error
    except jwt.PyJWTError as exc:
        raise _credentials_error from exc

    user = await db.get(User, int(user_id))
    if user is None:
        raise _credentials_error
    if user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is not active")
    return user


async def require_admin(current: User = Depends(get_current_user)) -> User:
    """Gate admin-only endpoints. Admin is determined by the configured email."""
    from app.core.entitlements import is_admin  # local import avoids cycle

    if not is_admin(current):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return current


__all__ = ["get_current_user", "require_admin", "oauth2_scheme"]
