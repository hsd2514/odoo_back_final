from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field, validator

from .common import BaseSchema


class UserBase(BaseSchema):
    full_name: Optional[str] = None
    email: EmailStr
    password_hash: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(BaseSchema):
    email: EmailStr = Field(..., description="User's email address", example="admin@example.com")
    full_name: Optional[str] = Field(None, description="User's full name", example="John Doe")
    phone: Optional[str] = Field(None, description="User's phone number", example="9098980900")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    confirm_password: str = Field(..., description="Confirm password (must match password)")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserLogin(BaseSchema):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class UserResponse(BaseSchema):
    message: str
    user_id: int
    email: str
    full_name: Optional[str]
    access_token: str
    token_type: str = "bearer"


class UserRead(UserBase):
    user_id: int = Field(alias="id")
    created_at: datetime




