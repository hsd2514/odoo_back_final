from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.user_service import create_user, get_user_by_email


def seed() -> None:
    db: Session = SessionLocal()
    try:
        if not get_user_by_email(db, email="admin@example.com"):
            create_user(db, email="admin@example.com", password="admin123", full_name="Admin User")
            print("Created default admin user: admin@example.com / admin123")
        else:
            print("Admin user already exists")
    finally:
        db.close()


if __name__ == "__main__":
    seed()


