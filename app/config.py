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
    
    # Password Reset
    password_reset_expire_minutes: int = int(os.getenv("PASSWORD_RESET_EXPIRE_MINUTES", "15"))

    # Gmail SMTP Configuration
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("GMAIL_USERNAME", "")  # Your Gmail address
    smtp_password: str = os.getenv("GMAIL_APP_PASSWORD", "")  # Gmail App Password
    email_from: str = os.getenv("EMAIL_FROM", os.getenv("GMAIL_USERNAME", "noreply@gmail.com"))
    email_from_name: str = os.getenv("EMAIL_FROM_NAME", "Odoo Rental System")

    # Stripe Payment Configuration
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_publishable_key: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_currency: str = os.getenv("STRIPE_CURRENCY", "usd")
    payment_success_url: str = os.getenv("PAYMENT_SUCCESS_URL", "http://localhost:3000/payment/success")
    payment_cancel_url: str = os.getenv("PAYMENT_CANCEL_URL", "http://localhost:3000/payment/cancel")

    # Misc
    app_name: str = os.getenv("APP_NAME", "Odoo Final Backend")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


