from __future__ import annotations

from typing import Optional

from .common import BaseSchema, InventoryStatus


class InventoryItemBase(BaseSchema):
    product_id: int
    sku: str | None = None
    serial: str | None = None
    qty: int | None = None
    status: InventoryStatus = InventoryStatus.AVAILABLE


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemRead(InventoryItemBase):
    item_id: int


