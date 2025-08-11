from __future__ import annotations

from datetime import datetime

from .common import BaseSchema


class NotificationBase(BaseSchema):
    user_id: int
    type: str
    payload: dict | None = None
    scheduled_for: datetime | None = None
    sent_at: datetime | None = None
    status: str | None = None


class NotificationCreate(NotificationBase):
    pass


class NotificationRead(NotificationBase):
    notification_id: int


