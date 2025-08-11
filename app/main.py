from __future__ import annotations

from fastapi import FastAPI

from .config import get_settings
from .database import Base, engine
from .routers import users
from .models import user as user_models  # ensure models imported
from .models import catalog, subscriptions, promotions, inventory, rentals, billing, loyalty


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    # Ensure models are imported and metadata is present
    Base.metadata.create_all(bind=engine)

    app.include_router(users.router)
    return app


app = create_app()


