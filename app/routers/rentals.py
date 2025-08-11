from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from math import ceil
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.rentals import RentalOrder, RentalItem
from ..models.catalog import Product
from ..models.inventory import InventoryItem
from ..utils.auth import require_roles, get_current_user, user_has_any_role


router = APIRouter(prefix="/rentals", tags=["rentals"])


# Pydantic Schemas for Request/Response
class CreateOrderRequest(BaseModel):
    customer_id: int = Field(..., description="ID of the customer placing the order")
    seller_id: int = Field(..., description="ID of the seller fulfilling the order")
    start_ts: datetime = Field(..., description="Start timestamp for the rental period (ISO 8601)")
    end_ts: datetime = Field(..., description="End timestamp for the rental period (ISO 8601)")


class AddItemRequest(BaseModel):
    product_id: int = Field(..., description="ID of the product being rented")
    inventory_item_id: Optional[int] = Field(None, description="Optional specific inventory item to reserve")
    qty: int = Field(1, ge=1, description="Quantity of items (minimum 1)")
    unit_price: Optional[float] = Field(None, ge=0, description="Override unit price (defaults to product base_price)")


class RentalItemResponse(BaseModel):
    rental_item_id: int
    rental_id: int
    product_id: int
    inventory_item_id: Optional[int]
    qty: int
    unit_price: float
    rental_period: Optional[str]
    line_total: float = Field(..., description="Computed line total: qty × unit_price × duration_units")

    class Config:
        from_attributes = True


class RentalOrderResponse(BaseModel):
    rental_id: int
    customer_id: int
    seller_id: int
    status: str
    total_amount: float
    start_ts: datetime
    end_ts: datetime
    items: List[RentalItemResponse] = Field(default=[], description="List of rental items")
    computed_total: float = Field(..., description="Server recomputed total for verification")

    class Config:
        from_attributes = True


# -- New: list orders for seller dashboard --
@router.get(
    "/orders",
    summary="List rental orders",
    description="Filter by status/invoice status/search; paging optional",
)
async def list_orders(
    status: str | None = None,
    invoice_status: str | None = None,
    q: str | None = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin", "Seller")),
):
    query = db.query(RentalOrder)
    if status:
        query = query.filter(RentalOrder.status == status)
    if q:
        # naive search on customer/seller ids or id
        if q.isdigit():
            query = query.filter(RentalOrder.rental_id == int(q))
    total = query.count()
    items = query.order_by(RentalOrder.rental_id.desc()).offset((page - 1) * limit).limit(limit).all()
    return {"items": items, "total": total, "page": page, "limit": limit}


# -- New: patch order status --
class OrderStatusPatch(BaseModel):
    status: str


@router.patch("/orders/{rental_id}/status", summary="Update rental order status")
async def patch_status(
    rental_id: int,
    payload: OrderStatusPatch,
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin", "Seller")),
):
    order = db.query(RentalOrder).filter(RentalOrder.rental_id == rental_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = payload.status
    db.commit()
    return {"updated": True}

# Helper Functions
def compute_duration_units(start_ts: datetime, end_ts: datetime, pricing_unit: str) -> int:
    """
    Compute duration units based on pricing unit.
    Always round up to avoid under-billing.
    """
    total_seconds = (end_ts - start_ts).total_seconds()
    total_hours = total_seconds / 3600
    
    if pricing_unit == "hour":
        return ceil(total_hours)
    elif pricing_unit == "day":
        return ceil(total_hours / 24)
    elif pricing_unit == "week":
        return ceil(total_hours / (24 * 7))
    elif pricing_unit == "month":
        # MVP approximation: 30 days per month
        total_days = total_hours / 24
        return ceil(total_days / 30)
    else:
        # Default to hourly if unknown unit
        return ceil(total_hours)


def recompute_order_total(db: Session, rental_id: int) -> Decimal:
    """
    Recompute total amount for an order by summing all line totals.
    """
    order = db.query(RentalOrder).filter(RentalOrder.rental_id == rental_id).first()
    if not order:
        return Decimal("0.00")
    
    total = Decimal("0.00")
    items = db.query(RentalItem).filter(RentalItem.rental_id == rental_id).all()
    
    for item in items:
        # Get product to determine pricing unit
        product = db.query(Product).filter(Product.product_id == item.product_id).first()
        if product:
            duration_units = compute_duration_units(order.start_ts, order.end_ts, product.pricing_unit)
            line_total = Decimal(str(item.qty)) * Decimal(str(item.unit_price)) * Decimal(str(duration_units))
            total += line_total
    
    return total


def get_item_line_total(db: Session, item: RentalItem) -> float:
    """Get computed line total for a rental item."""
    order = db.query(RentalOrder).filter(RentalOrder.rental_id == item.rental_id).first()
    product = db.query(Product).filter(Product.product_id == item.product_id).first()
    
    if not order or not product:
        return 0.0
    
    duration_units = compute_duration_units(order.start_ts, order.end_ts, product.pricing_unit)
    return float(item.qty * item.unit_price * duration_units)


# Endpoints
@router.post("/orders", 
             response_model=RentalOrderResponse, 
             status_code=status.HTTP_201_CREATED,
             summary="Create a new rental order",
             description="Create a new rental order with booked status. The order starts with zero total amount. End timestamp must be after start timestamp.")
async def create_order(order_data: CreateOrderRequest, db: Session = Depends(get_db), current=Depends(get_current_user)):
    """Create a new rental order"""
    
    # Validation: end_ts > start_ts
    if order_data.end_ts <= order_data.start_ts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End timestamp must be after start timestamp"
        )
    
    # Only the logged-in user can create an order (as customer)
    if order_data.customer_id and order_data.customer_id != current.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create order for another user")

    # Create order with status="booked" and total_amount=0
    new_order = RentalOrder(
        customer_id=current.user_id,
        seller_id=order_data.seller_id,
        status="booked",
        total_amount=0.0,
        start_ts=order_data.start_ts,
        end_ts=order_data.end_ts
    )
    
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    # Return order with empty items list and computed_total=0
    return RentalOrderResponse(
        rental_id=new_order.rental_id,
        customer_id=new_order.customer_id,
        seller_id=new_order.seller_id,
        status=new_order.status,
        total_amount=float(new_order.total_amount),
        start_ts=new_order.start_ts,
        end_ts=new_order.end_ts,
        items=[],
        computed_total=0.0
    )


@router.post("/orders/{rental_id}/items", 
             response_model=RentalItemResponse, 
             status_code=status.HTTP_201_CREATED,
             summary="Add item to rental order",
             description="""Add a product to a rental order. 
             
             Pricing behavior:
             - Duration units computed based on product pricing_unit (hour/day/week/month)
             - Always rounds up to avoid under-billing
             - Line total = qty × unit_price × duration_units
             - Order total automatically updated
             
             If inventory_item_id provided, the item will be reserved.""")
async def add_item_to_order(
    rental_id: int, 
    item_data: AddItemRequest, 
    db: Session = Depends(get_db),
    current=Depends(get_current_user)
):
    """Add item to rental order"""
    
    # Load and validate order
    order = db.query(RentalOrder).filter(RentalOrder.rental_id == rental_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rental order with ID {rental_id} not found"
        )
    
    # Authorization: owner or Admin/Seller
    if not (order.customer_id == current.user_id or user_has_any_role(db, current.user_id, ["Admin", "Seller"])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    # Validate order status
    if order.status not in ["booked", "active"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot add items to order with status '{order.status}'"
        )
    
    # Load and validate product
    product = db.query(Product).filter(Product.product_id == item_data.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {item_data.product_id} not found"
        )
    
    if not product.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with ID {item_data.product_id} is not active"
        )
    
    # Set unit price (use provided or default to product base_price)
    unit_price = item_data.unit_price if item_data.unit_price is not None else float(product.base_price)
    
    # Validate and handle inventory item if provided
    inventory_item = None
    if item_data.inventory_item_id:
        inventory_item = db.query(InventoryItem).filter(
            InventoryItem.item_id == item_data.inventory_item_id
        ).first()
        
        if not inventory_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory item with ID {item_data.inventory_item_id} not found"
            )
        
        # Validate inventory item belongs to the same product
        if inventory_item.product_id != item_data.product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Inventory item {item_data.inventory_item_id} does not belong to product {item_data.product_id}"
            )
        
        # Validate inventory item is available
        if inventory_item.status not in ["available", "reserved"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Inventory item {item_data.inventory_item_id} is not available (status: {inventory_item.status})"
            )
    
    # Compute rental period string
    rental_period = f"{order.start_ts.isoformat()},{order.end_ts.isoformat()}"
    
    # Create rental item
    rental_item = RentalItem(
        rental_id=rental_id,
        product_id=item_data.product_id,
        inventory_item_id=item_data.inventory_item_id,
        qty=item_data.qty,
        unit_price=unit_price,
        rental_period=rental_period
    )
    
    db.add(rental_item)
    db.commit()
    db.refresh(rental_item)
    
    # Reserve inventory item if provided
    if inventory_item:
        inventory_item.status = "reserved"
        db.commit()
    
    # Recompute and update order total
    new_total = recompute_order_total(db, rental_id)
    order.total_amount = float(new_total)
    db.commit()
    
    # Compute line total for response
    line_total = get_item_line_total(db, rental_item)
    
    return RentalItemResponse(
        rental_item_id=rental_item.rental_item_id,
        rental_id=rental_item.rental_id,
        product_id=rental_item.product_id,
        inventory_item_id=rental_item.inventory_item_id,
        qty=rental_item.qty,
        unit_price=rental_item.unit_price,
        rental_period=rental_item.rental_period,
        line_total=line_total
    )


@router.get("/orders/{rental_id}", 
            response_model=RentalOrderResponse,
            summary="Get rental order details",
            description="Retrieve a rental order with all items and computed totals. The computed_total field provides server-side verification of the total amount.")
async def get_order(rental_id: int, db: Session = Depends(get_db)):
    """Get rental order with items and computed totals"""
    
    # Load order
    order = db.query(RentalOrder).filter(RentalOrder.rental_id == rental_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rental order with ID {rental_id} not found"
        )
    
    # Load items
    items = db.query(RentalItem).filter(RentalItem.rental_id == rental_id).all()
    
    # Compute item responses with line totals
    item_responses = []
    for item in items:
        line_total = get_item_line_total(db, item)
        item_responses.append(RentalItemResponse(
            rental_item_id=item.rental_item_id,
            rental_id=item.rental_id,
            product_id=item.product_id,
            inventory_item_id=item.inventory_item_id,
            qty=item.qty,
            unit_price=item.unit_price,
            rental_period=item.rental_period,
            line_total=line_total
        ))
    
    # Recompute total for verification
    computed_total = float(recompute_order_total(db, rental_id))
    
    return RentalOrderResponse(
        rental_id=order.rental_id,
        customer_id=order.customer_id,
        seller_id=order.seller_id,
        status=order.status,
        total_amount=float(order.total_amount),
        start_ts=order.start_ts,
        end_ts=order.end_ts,
        items=item_responses,
        computed_total=computed_total
    )
