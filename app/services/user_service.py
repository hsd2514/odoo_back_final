from __future__ import annotations

from typing import Optional

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..models.user import User


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return password_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def create_user(db: Session, *, email: str, password: str, full_name: Optional[str] = None, phone: Optional[str] = None) -> User:
    user = User(email=email, password_hash=hash_password(password), full_name=full_name, phone=phone)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, *, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


