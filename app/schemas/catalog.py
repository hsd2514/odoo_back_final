from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field


# Category Schemas
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    parent_id: Optional[int] = Field(None, description="Parent category ID for hierarchical categories")


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Category name")
    parent_id: Optional[int] = Field(None, description="Parent category ID")


class CategoryResponse(CategoryBase):
    category_id: int = Field(..., description="Unique category identifier")

    class Config:
        from_attributes = True


# Product Asset Schemas  
class ProductAssetBase(BaseModel):
    asset_type: str = Field(..., min_length=1, max_length=20, description="Type of asset (image, video, document, etc.)")
    uri: str = Field(..., min_length=1, max_length=1024, description="Asset URI/URL")
    drm_protected: bool = Field(False, description="Whether the asset is DRM protected")


class ProductAssetCreate(ProductAssetBase):
    pass


class ProductAssetUpdate(BaseModel):
    asset_type: Optional[str] = Field(None, min_length=1, max_length=20, description="Type of asset")
    uri: Optional[str] = Field(None, min_length=1, max_length=1024, description="Asset URI/URL")
    drm_protected: Optional[bool] = Field(None, description="DRM protection status")


class ProductAssetResponse(ProductAssetBase):
    asset_id: int = Field(..., description="Unique asset identifier")
    product_id: int = Field(..., description="Associated product ID")

    class Config:
        from_attributes = True


# Product Schemas
class ProductBase(BaseModel):
    seller_id: int = Field(..., description="ID of the seller/user who owns this product")
    category_id: int = Field(..., description="Category this product belongs to")
    title: str = Field(..., min_length=1, max_length=255, description="Product title")
    base_price: float = Field(..., gt=0, description="Base price of the product")
    pricing_unit: str = Field(..., min_length=1, max_length=20, description="Pricing unit (hour, day, piece, etc.)")
    active: bool = Field(True, description="Whether the product is active/available")


class ProductCreate(ProductBase):
    assets: Optional[List[ProductAssetCreate]] = Field([], description="Product assets (images, videos, etc.)")


class ProductUpdate(BaseModel):
    seller_id: Optional[int] = Field(None, description="Seller ID")
    category_id: Optional[int] = Field(None, description="Category ID")
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Product title")
    base_price: Optional[float] = Field(None, gt=0, description="Base price")
    pricing_unit: Optional[str] = Field(None, min_length=1, max_length=20, description="Pricing unit")
    active: Optional[bool] = Field(None, description="Active status")


class ProductResponse(ProductBase):
    product_id: int = Field(..., description="Unique product identifier")
    assets: List[ProductAssetResponse] = Field([], description="Product assets")

    class Config:
        from_attributes = True


# List Response Schemas
class CategoryListResponse(BaseModel):
    categories: List[CategoryResponse] = Field(..., description="List of categories")
    total: int = Field(..., description="Total number of categories")


class ProductListResponse(BaseModel):
    products: List[ProductResponse] = Field(..., description="List of products")
    total: int = Field(..., description="Total number of products")


class ProductAssetListResponse(BaseModel):
    assets: List[ProductAssetResponse] = Field(..., description="List of product assets")
    total: int = Field(..., description="Total number of assets")
