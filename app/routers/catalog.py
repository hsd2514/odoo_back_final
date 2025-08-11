from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response, UploadFile, File
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.catalog import Category as CategoryModel, Product as ProductModel, ProductAsset as ProductAssetModel
from ..models.inventory import InventoryItem as InventoryItemModel
from ..schemas.categories import CategoryCreate, CategoryRead
from ..schemas.products import (
    ProductCreate,
    ProductRead,
    ProductAssetCreate,
    ProductAssetRead,
)
from ..schemas.common import PricingUnit
import hashlib
from ..utils.auth import require_roles


router = APIRouter(prefix="/catalog", tags=["catalog"])


# ---------- Categories ----------

@router.post(
    "/categories",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
    description="Create a new category. If parent_id is provided, it must reference an existing category.",
)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin", "Seller")),
) -> CategoryRead:
    if payload.parent_id is not None:
        parent = db.query(CategoryModel).get(payload.parent_id)
        if parent is None:
            raise HTTPException(status_code=400, detail="parent_id not found")

    category = CategoryModel(name=payload.name, parent_id=payload.parent_id)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category  # type: ignore[return-value]


@router.get(
    "/categories",
    response_model=List[CategoryRead],
    summary="List categories",
)
def list_categories(parent_id: Optional[int] = None, db: Session = Depends(get_db)) -> List[CategoryRead]:
    query = db.query(CategoryModel)
    if parent_id is not None:
        query = query.filter(CategoryModel.parent_id == parent_id)
    return query.all()  # type: ignore[return-value]


@router.get(
    "/categories/{category_id}",
    response_model=CategoryRead,
    summary="Get category by id",
)
def get_category(category_id: int, db: Session = Depends(get_db)) -> CategoryRead:
    category = db.query(CategoryModel).get(category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category  # type: ignore[return-value]


@router.patch(
    "/categories/{category_id}",
    response_model=CategoryRead,
    summary="Update category",
)
def update_category(
    category_id: int,
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin", "Seller")),
) -> CategoryRead:
    category = db.query(CategoryModel).get(category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    if payload.parent_id is not None:
        parent = db.query(CategoryModel).get(payload.parent_id)
        if parent is None:
            raise HTTPException(status_code=400, detail="parent_id not found")

    category.name = payload.name
    category.parent_id = payload.parent_id
    db.commit()
    db.refresh(category)
    return category  # type: ignore[return-value]


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete category",
    description="Delete a category that has no products referencing it. Returns 409 if in-use.",
    response_class=Response,
)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin", "Seller")),
) -> Response:
    category = db.query(CategoryModel).get(category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    in_use = db.query(ProductModel).filter(ProductModel.category_id == category_id).first()
    if in_use is not None:
        raise HTTPException(status_code=409, detail="Category has products; cannot delete")

    db.delete(category)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Products ----------

ALLOWED_UNITS = {unit.value for unit in PricingUnit}


@router.post(
    "/products",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
    description="Create a product under a category. pricing_unit must be one of hour, day, week, month.",
)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin", "Seller")),
) -> ProductRead:
    # Validate category
    if db.query(CategoryModel).get(payload.category_id) is None:
        raise HTTPException(status_code=400, detail="category_id not found")

    # Validate pricing unit and price
    if payload.pricing_unit not in ALLOWED_UNITS:
        raise HTTPException(status_code=400, detail=f"pricing_unit must be one of {sorted(ALLOWED_UNITS)}")
    if payload.base_price < 0:
        raise HTTPException(status_code=400, detail="base_price must be >= 0")

    product = ProductModel(
        seller_id=payload.seller_id,
        category_id=payload.category_id,
        title=payload.title,
        base_price=payload.base_price,
        pricing_unit=payload.pricing_unit,
        active=payload.active,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product  # type: ignore[return-value]


@router.get(
    "/products",
    response_model=List[ProductRead],
    summary="List products",
)
def list_products(
    category_id: Optional[int] = None,
    seller_id: Optional[int] = None,
    active: Optional[bool] = None,
    q: Optional[str] = Query(None, description="Title contains"),
    db: Session = Depends(get_db),
) -> List[ProductRead]:
    query = db.query(ProductModel)
    if category_id is not None:
        query = query.filter(ProductModel.category_id == category_id)
    if seller_id is not None:
        query = query.filter(ProductModel.seller_id == seller_id)
    if active is not None:
        query = query.filter(ProductModel.active == active)
    if q:
        query = query.filter(ProductModel.title.ilike(f"%{q}%"))
    return query.all()  # type: ignore[return-value]


@router.get(
    "/products/{product_id}",
    response_model=ProductRead,
    summary="Get product",
)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductRead:
    product = db.query(ProductModel).get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product  # type: ignore[return-value]


@router.patch(
    "/products/{product_id}",
    response_model=ProductRead,
    summary="Update product",
)
def update_product(
    product_id: int,
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin", "Seller")),
) -> ProductRead:
    product = db.query(ProductModel).get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Category exists if provided
    if payload.category_id and db.query(CategoryModel).get(payload.category_id) is None:
        raise HTTPException(status_code=400, detail="category_id not found")

    # Allowed unit and price
    if payload.pricing_unit and payload.pricing_unit not in ALLOWED_UNITS:
        raise HTTPException(status_code=400, detail=f"pricing_unit must be one of {sorted(ALLOWED_UNITS)}")
    if payload.base_price is not None and payload.base_price < 0:
        raise HTTPException(status_code=400, detail="base_price must be >= 0")

    # Update fields (simple replace from payload)
    product.seller_id = payload.seller_id
    product.category_id = payload.category_id
    product.title = payload.title
    product.base_price = payload.base_price
    product.pricing_unit = payload.pricing_unit
    product.active = payload.active
    db.commit()
    db.refresh(product)
    return product  # type: ignore[return-value]


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product",
    description="Delete a product that has no inventory items referencing it. Returns 409 if in-use.",
    response_class=Response,
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin", "Seller")),
) -> Response:
    product = db.query(ProductModel).get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    linked = db.query(InventoryItemModel).filter(InventoryItemModel.product_id == product_id).first()
    if linked is not None:
        raise HTTPException(status_code=409, detail="Product has inventory items; cannot delete")

    db.delete(product)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Product Assets ----------

ALLOWED_ASSETS = {"image", "3d", "ar"}


@router.post(
    "/products/{product_id}/assets",
    response_model=ProductAssetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add product asset",
)
def create_asset(
    product_id: int,
    payload: ProductAssetCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin", "Seller")),
) -> ProductAssetRead:
    product = db.query(ProductModel).get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if payload.asset_type not in ALLOWED_ASSETS:
        raise HTTPException(status_code=400, detail="asset_type must be one of 'image','3d','ar'")
    if not payload.uri:
        raise HTTPException(status_code=400, detail="uri is required")

    asset = ProductAssetModel(
        product_id=product_id,
        asset_type=payload.asset_type,
        uri=payload.uri,
        drm_protected=bool(payload.drm_protected),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset  # type: ignore[return-value]


@router.get(
    "/products/{product_id}/assets",
    response_model=List[ProductAssetRead],
    summary="List product assets",
)
def list_assets(product_id: int, db: Session = Depends(get_db)) -> List[ProductAssetRead]:
    product = db.query(ProductModel).get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return (
        db.query(ProductAssetModel).filter(ProductAssetModel.product_id == product_id).all()
    )  # type: ignore[return-value]


@router.delete(
    "/products/{product_id}/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product asset",
    response_class=Response,
)
def delete_asset(
    product_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin", "Seller")),
) -> Response:
    asset = db.query(ProductAssetModel).get(asset_id)
    if asset is None or asset.product_id != product_id:
        raise HTTPException(status_code=404, detail="Asset not found for this product")
    db.delete(asset)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Inline upload (bytea) ---
@router.post(
    "/products/{product_id}/assets/upload",
    response_model=ProductAssetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload product image/asset (stored inline)",
)
def upload_asset(
    product_id: int,
    file: UploadFile = File(...),
    asset_type: str = "image",
    drm_protected: bool = False,
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin", "Seller")),
) -> ProductAssetRead:
    product = db.query(ProductModel).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if asset_type not in ALLOWED_ASSETS:
        raise HTTPException(status_code=400, detail="asset_type must be one of 'image','3d','ar'")
    data = file.file.read()
    sha = hashlib.sha256(data).hexdigest()
    asset = ProductAssetModel(
        product_id=product_id,
        asset_type=asset_type,
        uri=None,
        drm_protected=bool(drm_protected),
        filename=file.filename,
        content_type=file.content_type,
        size=len(data),
        sha256=sha,
        data=data,
    )
    db.add(asset)
    db.commit(); db.refresh(asset)
    return asset  # type: ignore[return-value]

