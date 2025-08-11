from __future__ import annotations

from fastapi import FastAPI

from .config import get_settings
from .database import Base, engine
from .routers import users


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    # Import models to ensure they're registered with SQLAlchemy
    from .models import user  # Only import user model for now

    # Create database tables
    Base.metadata.create_all(bind=engine)

    app.include_router(users.router)
    return app


app = create_app()


