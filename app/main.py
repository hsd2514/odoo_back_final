from __future__ import annotations

from fastapi import FastAPI

from .config import get_settings
from .database import Base, engine
from .routers import users, catalog, rentals


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    # Import models to ensure they're registered with SQLAlchemy
    from .models import user, catalog as catalog_models, rentals as rental_models

    # Create database tables
    Base.metadata.create_all(bind=engine)

    app.include_router(users.router)
    app.include_router(catalog.router)
    app.include_router(rentals.router)
    return app


app = create_app()


