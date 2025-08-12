from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..utils.auth import get_current_user
from ..models.user import Role, UserRole


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/me",
    summary="Current user profile with roles (alias of /users/me)",
)
async def me_alias(current=Depends(get_current_user), db: Session = Depends(get_db)):
    role_rows = (
        db.query(Role.name)
        .join(UserRole, Role.role_id == UserRole.role_id)
        .filter(UserRole.user_id == current.user_id)
        .all()
    )
    roles = [name for (name,) in role_rows]
    return {
        "user_id": current.user_id,
        "email": current.email,
        "full_name": current.full_name,
        "roles": roles,
    }


