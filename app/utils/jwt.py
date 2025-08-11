from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import jwt

from ..config import get_settings


def create_access_token(subject: str | int, expires_delta_minutes: int | None = None) -> str:
    settings = get_settings()
    expire_minutes = expires_delta_minutes if expires_delta_minutes is not None else settings.access_token_expire_minutes
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=expire_minutes)

    to_encode: Dict[str, Any] = {"sub": str(subject), "exp": expire}
    token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token


def create_password_reset_token(email: str) -> str:
    """Create a password reset token with shorter expiration time"""
    settings = get_settings()
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=settings.password_reset_expire_minutes)
    
    to_encode: Dict[str, Any] = {
        "sub": email,
        "exp": expire,
        "type": "password_reset"
    }
    token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token


def verify_password_reset_token(token: str) -> str | None:
    """Verify password reset token and return email if valid"""
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        
        # Check if it's a password reset token
        if payload.get("type") != "password_reset":
            return None
            
        email = payload.get("sub")
        return email
    except jwt.JWTError:
        return None


