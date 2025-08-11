from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.user import UserCreate, UserLogin, UserRead
from ..services.user_service import create_user, get_user_by_email, verify_password
from ..utils.jwt import create_access_token


router = APIRouter(prefix="/users", tags=["users"])




