from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine
from .routers import users
from .routers import inventory
from .routers import catalog


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )

    # Import models to ensure they're registered with SQLAlchemy
    from .models import user  # Only import user model for now

    # Create database tables
    Base.metadata.create_all(bind=engine)

    app.include_router(users.router)
    app.include_router(inventory.router)
    app.include_router(catalog.router)
    return app


app = create_app()


