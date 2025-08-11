from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rental_id: Mapped[int] = mapped_column(ForeignKey("rental_orders.rental_id"), nullable=False)
    amount_due: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    status: Mapped[str | None] = mapped_column(String(20))
    due_date: Mapped[str | None] = mapped_column(String(50))


class Payment(Base):
    __tablename__ = "payments"

    payment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.invoice_id"))
    rental_id: Mapped[int] = mapped_column(ForeignKey("rental_orders.rental_id"), nullable=False)
    gateway: Mapped[str | None] = mapped_column(String(50))
    txn_id: Mapped[str | None] = mapped_column(String(100))
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    paid_at: Mapped[str | None] = mapped_column(String(50))


