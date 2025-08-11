from __future__ import annotations

from .common import BaseSchema


class RoleBase(BaseSchema):
    name: str  # admin/seller/customer
    description: str | None = None


class RoleCreate(RoleBase):
    pass


class RoleRead(RoleBase):
    role_id: int


class UserRoleBase(BaseSchema):
    user_id: int
    role_id: int


class UserRoleCreate(UserRoleBase):
    pass


class UserRoleRead(UserRoleBase):
    id: int


