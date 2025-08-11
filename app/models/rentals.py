from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class RentalOrder(Base):
    __tablename__ = "rental_orders"

    rental_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    items: Mapped[list["RentalItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class RentalItem(Base):
    __tablename__ = "rental_items"

    rental_item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rental_id: Mapped[int] = mapped_column(ForeignKey("rental_orders.rental_id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"), nullable=False)
    inventory_item_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_items.item_id"))
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    rental_period: Mapped[str | None] = mapped_column(String(100))

    order: Mapped[RentalOrder] = relationship("RentalOrder", back_populates="items")


class Schedule(Base):
    __tablename__ = "schedules"

    schedule_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rental_id: Mapped[int] = mapped_column(ForeignKey("rental_orders.rental_id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.product_id"))
    metadata: Mapped[dict | None] = mapped_column(nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict | None] = mapped_column(nullable=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str | None] = mapped_column(String(20))


class HandoverQR(Base):
    __tablename__ = "handover_qr"

    qr_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rental_id: Mapped[int] = mapped_column(ForeignKey("rental_orders.rental_id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    qr_token: Mapped[str] = mapped_column(String(255), nullable=False)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


