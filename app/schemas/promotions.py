from __future__ import annotations

from datetime import date

from .common import BaseSchema, DiscountType


class PromotionBase(BaseSchema):
    code: str
    discount_type: DiscountType
    value: float
    valid_from: date
    valid_to: date


class PromotionCreate(PromotionBase):
    pass


class PromotionRead(PromotionBase):
    promo_id: int


