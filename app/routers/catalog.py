from __future__ import annotations

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.catalog import (
    CategoryCreate, CategoryUpdate, CategoryResponse, CategoryListResponse,
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse,
    ProductAssetCreate, ProductAssetUpdate, ProductAssetResponse, ProductAssetListResponse
)
from ..services import catalog_service


router = APIRouter(prefix="/catalog", tags=["catalog"])


# Category Endpoints
@router.post("/categories", 
             response_model=CategoryResponse, 
             status_code=status.HTTP_201_CREATED,
             summary="Create a new category",
             description="Create a new product category. Categories can be hierarchical with parent_id.")
async def create_category(
    category_data: CategoryCreate, 
    db: Session = Depends(get_db)
):
    """Create a new category"""
    # Check if parent category exists if parent_id is provided
    if category_data.parent_id:
        parent = catalog_service.get_category_by_id(db, category_data.parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parent category with ID {category_data.parent_id} not found"
            )
    
    return catalog_service.create_category(db, category_data)


@router.get("/categories", 
            response_model=CategoryListResponse,
            summary="Get categories",
            description="Retrieve categories with optional filtering by parent_id and pagination.")
async def get_categories(
    skip: int = Query(0, ge=0, description="Number of categories to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of categories to return"),
    parent_id: Optional[int] = Query(None, description="Filter by parent category ID"),
    db: Session = Depends(get_db)
):
    """Get categories with optional filtering"""
    categories = catalog_service.get_categories(db, skip=skip, limit=limit, parent_id=parent_id)
    total = catalog_service.count_categories(db, parent_id=parent_id)
    
    return CategoryListResponse(categories=categories, total=total)


@router.get("/categories/{category_id}", 
            response_model=CategoryResponse,
            summary="Get category by ID",
            description="Retrieve a specific category by its ID.")
async def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get category by ID"""
    category = catalog_service.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} not found"
        )
    return category


@router.put("/categories/{category_id}", 
            response_model=CategoryResponse,
            summary="Update category",
            description="Update a category's information.")
async def update_category(
    category_id: int, 
    category_data: CategoryUpdate, 
    db: Session = Depends(get_db)
):
    """Update category"""
    # Check if parent category exists if parent_id is being updated
    if category_data.parent_id:
        parent = catalog_service.get_category_by_id(db, category_data.parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parent category with ID {category_data.parent_id} not found"
            )
    
    category = catalog_service.update_category(db, category_id, category_data)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} not found"
        )
    return category


@router.delete("/categories/{category_id}", 
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete category",
               description="Delete a category. This will fail if the category has child categories or products.")
async def delete_category(category_id: int, db: Session = Depends(get_db)):
    """Delete category"""
    success = catalog_service.delete_category(db, category_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} not found"
        )


# Product Endpoints
@router.post("/products", 
             response_model=ProductResponse, 
             status_code=status.HTTP_201_CREATED,
             summary="Create a new product",
             description="Create a new product with optional assets.")
async def create_product(
    product_data: ProductCreate, 
    db: Session = Depends(get_db)
):
    """Create a new product"""
    # Verify category exists
    category = catalog_service.get_category_by_id(db, product_data.category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with ID {product_data.category_id} not found"
        )
    
    return catalog_service.create_product(db, product_data)


@router.get("/products", 
            response_model=ProductListResponse,
            summary="Get products",
            description="Retrieve products with optional filtering and pagination.")
async def get_products(
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of products to return"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    seller_id: Optional[int] = Query(None, description="Filter by seller ID"),
    active_only: bool = Query(True, description="Only return active products"),
    db: Session = Depends(get_db)
):
    """Get products with optional filtering"""
    products = catalog_service.get_products(
        db, skip=skip, limit=limit, 
        category_id=category_id, seller_id=seller_id, active_only=active_only
    )
    total = catalog_service.count_products(
        db, category_id=category_id, seller_id=seller_id, active_only=active_only
    )
    
    return ProductListResponse(products=products, total=total)


@router.get("/products/{product_id}", 
            response_model=ProductResponse,
            summary="Get product by ID",
            description="Retrieve a specific product by its ID with all assets.")
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get product by ID"""
    product = catalog_service.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    return product


@router.put("/products/{product_id}", 
            response_model=ProductResponse,
            summary="Update product",
            description="Update a product's information.")
async def update_product(
    product_id: int, 
    product_data: ProductUpdate, 
    db: Session = Depends(get_db)
):
    """Update product"""
    # Verify category exists if being updated
    if product_data.category_id:
        category = catalog_service.get_category_by_id(db, product_data.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with ID {product_data.category_id} not found"
            )
    
    product = catalog_service.update_product(db, product_id, product_data)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    return product


@router.delete("/products/{product_id}", 
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete product",
               description="Delete a product and all its assets.")
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete product"""
    success = catalog_service.delete_product(db, product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )


# Product Asset Endpoints
@router.post("/products/{product_id}/assets", 
             response_model=ProductAssetResponse, 
             status_code=status.HTTP_201_CREATED,
             summary="Add asset to product",
             description="Add a new asset (image, video, document) to a product.")
async def create_product_asset(
    product_id: int,
    asset_data: ProductAssetCreate, 
    db: Session = Depends(get_db)
):
    """Create a new product asset"""
    asset = catalog_service.create_product_asset(db, product_id, asset_data)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    return asset


@router.get("/products/{product_id}/assets", 
            response_model=ProductAssetListResponse,
            summary="Get product assets",
            description="Retrieve all assets for a specific product.")
async def get_product_assets(product_id: int, db: Session = Depends(get_db)):
    """Get all assets for a product"""
    # Verify product exists
    product = catalog_service.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    assets = catalog_service.get_product_assets(db, product_id)
    total = catalog_service.count_product_assets(db, product_id)
    
    return ProductAssetListResponse(assets=assets, total=total)


@router.get("/assets/{asset_id}", 
            response_model=ProductAssetResponse,
            summary="Get asset by ID",
            description="Retrieve a specific asset by its ID.")
async def get_product_asset(asset_id: int, db: Session = Depends(get_db)):
    """Get product asset by ID"""
    asset = catalog_service.get_product_asset_by_id(db, asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found"
        )
    return asset


@router.put("/assets/{asset_id}", 
            response_model=ProductAssetResponse,
            summary="Update asset",
            description="Update an asset's information.")
async def update_product_asset(
    asset_id: int, 
    asset_data: ProductAssetUpdate, 
    db: Session = Depends(get_db)
):
    """Update product asset"""
    asset = catalog_service.update_product_asset(db, asset_id, asset_data)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found"
        )
    return asset


@router.delete("/assets/{asset_id}", 
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete asset",
               description="Delete a product asset.")
async def delete_product_asset(asset_id: int, db: Session = Depends(get_db)):
    """Delete product asset"""
    success = catalog_service.delete_product_asset(db, asset_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found"
        )
