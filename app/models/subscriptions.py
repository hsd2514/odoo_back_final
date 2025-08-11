from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    plan_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    discount_pct: Mapped[float] = mapped_column(nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    included_products: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


