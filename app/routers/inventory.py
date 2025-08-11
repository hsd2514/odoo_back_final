from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.inventory import InventoryItem as InventoryItemModel
from ..schemas.inventory import (
    InventoryItemCreate,
    InventoryItemRead,
)
from ..schemas.common import InventoryStatus


router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post(
    "/items",
    response_model=InventoryItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create inventory item",
)
def create_item(payload: InventoryItemCreate, db: Session = Depends(get_db)):
    item = InventoryItemModel(
        product_id=payload.product_id,
        sku=payload.sku,
        serial=payload.serial,
        qty=payload.qty,
        status=payload.status.value if isinstance(payload.status, InventoryStatus) else payload.status,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get(
    "/items/{item_id}",
    response_model=InventoryItemRead,
    summary="Get inventory item by id",
)
def get_item(item_id: int = Path(...), db: Session = Depends(get_db)):
    item = db.query(InventoryItemModel).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get(
    "/items",
    response_model=list[InventoryItemRead],
    summary="List inventory items",
)
def list_items(
    status_filter: InventoryStatus | None = Query(None, alias="status"),
    product_id: int | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(InventoryItemModel)
    if product_id is not None:
        q = q.filter(InventoryItemModel.product_id == product_id)
    if status_filter is not None:
        q = q.filter(InventoryItemModel.status == status_filter.value)
    return q.all()


@router.patch(
    "/items/{item_id}/status",
    response_model=InventoryItemRead,
    summary="Update inventory item status",
    description="Transition status among available → reserved → rented or back to available.",
)
def update_status(
    item_id: int,
    new_status: InventoryStatus = Query(..., description="New status"),
    db: Session = Depends(get_db),
):
    item = db.query(InventoryItemModel).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    valid = {s.value for s in InventoryStatus}
    if new_status.value not in valid:
        raise HTTPException(status_code=400, detail="Invalid status")

    # basic transition logic: allow any for now; customize as needed
    item.status = new_status.value
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete inventory item",
)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(InventoryItemModel).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return None


