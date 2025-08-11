from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import Role, UserRole
from ..utils.auth import require_roles


router = APIRouter(prefix="/roles", tags=["roles"])


class RoleCreate(BaseModel):
    name: str = Field(..., examples=["Admin", "Seller", "Customer"])
    description: str | None = None


class UserRoleAssign(BaseModel):
    user_id: int
    role_id: int


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED, summary="Create role")
def create_role(payload: RoleCreate, db: Session = Depends(get_db), _: None = Depends(require_roles("Admin"))):
    existing = db.query(Role).filter(Role.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Role name already exists")
    role = Role(name=payload.name, description=payload.description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return {"role_id": role.role_id, "name": role.name}


@router.get("/", response_model=list[dict], summary="List roles")
def list_roles(db: Session = Depends(get_db)):
    roles = db.query(Role).all()
    return [{"role_id": r.role_id, "name": r.name, "description": r.description} for r in roles]


@router.post("/assign", response_model=dict, status_code=status.HTTP_201_CREATED, summary="Assign role to user")
def assign_user_role(payload: UserRoleAssign, db: Session = Depends(get_db), _: None = Depends(require_roles("Admin"))):
    exists = (
        db.query(UserRole)
        .filter(UserRole.user_id == payload.user_id, UserRole.role_id == payload.role_id)
        .first()
    )
    if exists:
        return {"assigned": True}
    ur = UserRole(user_id=payload.user_id, role_id=payload.role_id)
    db.add(ur)
    db.commit()
    return {"assigned": True}


