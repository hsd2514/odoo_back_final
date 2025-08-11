from __future__ import annotations

from datetime import datetime

from .common import BaseSchema


class PaymentBase(BaseSchema):
    invoice_id: int | None = None
    rental_id: int
    gateway: str | None = None
    txn_id: str | None = None
    amount: float
    paid_at: datetime | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentRead(PaymentBase):
    payment_id: int


