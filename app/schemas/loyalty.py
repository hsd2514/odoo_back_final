from __future__ import annotations

from .common import BaseSchema


class LoyaltyAccountBase(BaseSchema):
    user_id: int
    points_balance: int = 0
    tier: str | None = None


class LoyaltyAccountCreate(LoyaltyAccountBase):
    pass


class LoyaltyAccountRead(LoyaltyAccountBase):
    account_id: int


