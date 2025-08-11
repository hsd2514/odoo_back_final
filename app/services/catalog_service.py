from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.catalog import Category, Product, ProductAsset
from ..schemas.catalog import (
    CategoryCreate, CategoryUpdate, 
    ProductCreate, ProductUpdate,
    ProductAssetCreate, ProductAssetUpdate
)


# Category Services
def create_category(db: Session, category_data: CategoryCreate) -> Category:
    """Create a new category"""
    category = Category(**category_data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def get_category_by_id(db: Session, category_id: int) -> Optional[Category]:
    """Get category by ID"""
    return db.query(Category).filter(Category.category_id == category_id).first()


def get_categories(db: Session, skip: int = 0, limit: int = 100, parent_id: Optional[int] = None) -> List[Category]:
    """Get categories with optional filtering by parent_id"""
    query = db.query(Category)
    
    if parent_id is not None:
        query = query.filter(Category.parent_id == parent_id)
    
    return query.offset(skip).limit(limit).all()


def update_category(db: Session, category_id: int, category_data: CategoryUpdate) -> Optional[Category]:
    """Update category"""
    category = get_category_by_id(db, category_id)
    if not category:
        return None
    
    update_data = category_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> bool:
    """Delete category"""
    category = get_category_by_id(db, category_id)
    if not category:
        return False
    
    db.delete(category)
    db.commit()
    return True


# Product Services
def create_product(db: Session, product_data: ProductCreate) -> Product:
    """Create a new product with assets"""
    # Create product without assets first
    product_dict = product_data.model_dump(exclude={'assets'})
    product = Product(**product_dict)
    db.add(product)
    db.flush()  # Get the product_id without committing
    
    # Create associated assets
    if product_data.assets:
        for asset_data in product_data.assets:
            asset = ProductAsset(product_id=product.product_id, **asset_data.model_dump())
            db.add(asset)
    
    db.commit()
    db.refresh(product)
    return product


def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
    """Get product by ID with assets"""
    return db.query(Product).filter(Product.product_id == product_id).first()


def get_products(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    category_id: Optional[int] = None,
    seller_id: Optional[int] = None,
    active_only: bool = True
) -> List[Product]:
    """Get products with optional filtering"""
    query = db.query(Product)
    
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    
    if seller_id is not None:
        query = query.filter(Product.seller_id == seller_id)
    
    if active_only:
        query = query.filter(Product.active == True)
    
    return query.offset(skip).limit(limit).all()


def update_product(db: Session, product_id: int, product_data: ProductUpdate) -> Optional[Product]:
    """Update product"""
    product = get_product_by_id(db, product_id)
    if not product:
        return None
    
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> bool:
    """Delete product and its assets"""
    product = get_product_by_id(db, product_id)
    if not product:
        return False
    
    db.delete(product)
    db.commit()
    return True


# Product Asset Services
def create_product_asset(db: Session, product_id: int, asset_data: ProductAssetCreate) -> Optional[ProductAsset]:
    """Create a new product asset"""
    # Verify product exists
    product = get_product_by_id(db, product_id)
    if not product:
        return None
    
    asset = ProductAsset(product_id=product_id, **asset_data.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def get_product_asset_by_id(db: Session, asset_id: int) -> Optional[ProductAsset]:
    """Get product asset by ID"""
    return db.query(ProductAsset).filter(ProductAsset.asset_id == asset_id).first()


def get_product_assets(db: Session, product_id: int) -> List[ProductAsset]:
    """Get all assets for a product"""
    return db.query(ProductAsset).filter(ProductAsset.product_id == product_id).all()


def update_product_asset(db: Session, asset_id: int, asset_data: ProductAssetUpdate) -> Optional[ProductAsset]:
    """Update product asset"""
    asset = get_product_asset_by_id(db, asset_id)
    if not asset:
        return None
    
    update_data = asset_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)
    
    db.commit()
    db.refresh(asset)
    return asset


def delete_product_asset(db: Session, asset_id: int) -> bool:
    """Delete product asset"""
    asset = get_product_asset_by_id(db, asset_id)
    if not asset:
        return False
    
    db.delete(asset)
    db.commit()
    return True


# Count functions for pagination
def count_categories(db: Session, parent_id: Optional[int] = None) -> int:
    """Count categories"""
    query = db.query(Category)
    if parent_id is not None:
        query = query.filter(Category.parent_id == parent_id)
    return query.count()


def count_products(
    db: Session,
    category_id: Optional[int] = None,
    seller_id: Optional[int] = None,
    active_only: bool = True
) -> int:
    """Count products"""
    query = db.query(Product)
    
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    
    if seller_id is not None:
        query = query.filter(Product.seller_id == seller_id)
    
    if active_only:
        query = query.filter(Product.active == True)
    
    return query.count()


def count_product_assets(db: Session, product_id: int) -> int:
    """Count assets for a product"""
    return db.query(ProductAsset).filter(ProductAsset.product_id == product_id).count()
