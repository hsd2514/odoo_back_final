from __future__ import annotations

from typing import Optional

from .common import BaseSchema, PricingUnit


class ProductBase(BaseSchema):
    title: str
    seller_id: int
    category_id: int
    base_price: float
    pricing_unit: PricingUnit
    active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    product_id: int


class ProductAssetBase(BaseSchema):
    product_id: int
    asset_type: str  # image/3d/ar
    uri: str
    drm_protected: bool = False


class ProductAssetCreate(ProductAssetBase):
    pass


class ProductAssetRead(ProductAssetBase):
    asset_id: int


