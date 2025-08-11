from __future__ import annotations

from datetime import datetime

from .common import BaseSchema


class InvoiceBase(BaseSchema):
    rental_id: int
    amount_due: float
    amount_paid: float = 0
    status: str | None = None
    due_date: datetime | None = None


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceRead(InvoiceBase):
    invoice_id: int


