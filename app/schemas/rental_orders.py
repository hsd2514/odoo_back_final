from __future__ import annotations

from datetime import datetime

from .common import BaseSchema


class RentalOrderBase(BaseSchema):
    customer_id: int
    seller_id: int
    status: str
    total_amount: float
    start_ts: datetime
    end_ts: datetime


class RentalOrderCreate(RentalOrderBase):
    pass


class RentalOrderRead(RentalOrderBase):
    rental_id: int


