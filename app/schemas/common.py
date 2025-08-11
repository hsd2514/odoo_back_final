from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class PricingUnit(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class InventoryStatus(str, Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    RENTED = "rented"


class ScheduleType(str, Enum):
    PICKUP = "pickup"
    RETURN = "return"


class AssetType(str, Enum):
    IMAGE = "image"
    THREE_D = "3d"
    AR = "ar"


class HandoverType(str, Enum):
    PICKUP = "pickup"
    RETURN = "return"


Money = Decimal


