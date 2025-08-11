from __future__ import annotations

from typing import Optional

from .common import BaseSchema


class CategoryBase(BaseSchema):
    name: str
    parent_id: int | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    category_id: int


