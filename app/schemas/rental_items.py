from __future__ import annotations

from typing import Optional

from .common import BaseSchema


class RentalItemBase(BaseSchema):
    rental_id: int
    product_id: int
    inventory_item_id: int | None = None
    qty: int
    unit_price: float
    rental_period: tuple[str, str] | None = None  # (start,end) ISO strings


class RentalItemCreate(RentalItemBase):
    pass


class RentalItemRead(RentalItemBase):
    rental_item_id: int


