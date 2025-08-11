from __future__ import annotations

from datetime import datetime

from .common import BaseSchema, ScheduleType


class ScheduleBase(BaseSchema):
    rental_id: int
    type: ScheduleType
    scheduled_for: datetime
    actual_at: datetime | None = None
    assigned_to: int | None = None  # FK -> users


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleRead(ScheduleBase):
    schedule_id: int


