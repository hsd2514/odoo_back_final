from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv


# Load variables from a local .env file if present
load_dotenv()


class Settings:
    """Application settings resolved from environment variables.

    Defaults are development-friendly so the app can run out of the box.
    """

    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/odoo_final")

    # Security
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")

    # Misc
    app_name: str = os.getenv("APP_NAME", "Odoo Final Backend")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


