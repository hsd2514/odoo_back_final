from __future__ import annotations

from datetime import datetime

from .common import BaseSchema


class EventBase(BaseSchema):
    occurred_at: datetime
    event_type: str
    user_id: int | None = None
    product_id: int | None = None
    metadata: dict | None = None


class EventCreate(EventBase):
    pass


class EventRead(EventBase):
    event_id: int


