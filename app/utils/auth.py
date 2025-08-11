from __future__ import annotations

from typing import Callable, Iterable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models.user import User, UserRole, Role


bearer_scheme = HTTPBearer(auto_error=False)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:  # includes ExpiredSignatureError
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.scheme.lower() == "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")

    payload = decode_access_token(credentials.credentials)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = db.query(User).filter(User.user_id == int(user_id_str)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def user_has_any_role(db: Session, user_id: int, allowed_roles: Iterable[str]) -> bool:
    role_names = (
        db.query(Role.name)
        .join(UserRole, Role.role_id == UserRole.role_id)
        .filter(UserRole.user_id == user_id)
        .all()
    )
    current = {name for (name,) in role_names}
    return any(role in current for role in allowed_roles)


def require_roles(*allowed_roles: str) -> Callable:
    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not user_has_any_role(db, current_user.user_id, allowed_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency


