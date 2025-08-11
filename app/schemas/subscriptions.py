from __future__ import annotations

from typing import Optional

from pydantic import Field

from .common import BaseSchema


class SubscriptionPlanBase(BaseSchema):
    name: str
    discount_pct: float = Field(ge=0, le=100)
    duration_days: int
    included_products: list[int] | None = None


class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass


class SubscriptionPlanRead(SubscriptionPlanBase):
    plan_id: int


