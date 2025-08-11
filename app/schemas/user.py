from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field

from .common import BaseSchema


class UserBase(BaseSchema):
    full_name: Optional[str] = None
    email: EmailStr
    password_hash: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(BaseSchema):
    full_name: Optional[str] = None
    email: EmailStr
    password: str = Field(min_length=6)
    phone: Optional[str] = None


class UserLogin(BaseSchema):
    email: EmailStr
    password: str


class UserRead(UserBase):
    user_id: int = Field(alias="id")
    created_at: datetime




