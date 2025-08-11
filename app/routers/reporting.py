from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.rentals import RentalOrder, RentalItem
from ..models.catalog import Product, Category
from ..models.billing import Invoice
from ..utils.auth import require_roles


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
def summary(from_ts: datetime | None = None, to_ts: datetime | None = None, db: Session = Depends(get_db), _: None = Depends(require_roles("Admin", "Seller"))):
    q_orders = db.query(RentalOrder)
    q_inv = db.query(Invoice)
    if from_ts and to_ts:
        q_orders = q_orders.filter(RentalOrder.start_ts >= from_ts, RentalOrder.end_ts <= to_ts)
        q_inv = q_inv.filter(Invoice.due_date == None)  # placeholder, adjust if due_date set

    rentals = q_orders.count()
    revenue = db.query(func.coalesce(func.sum(Invoice.amount_paid), 0)).scalar() or 0

    top_products = (
        db.query(Product.title, func.count(RentalItem.product_id).label("ordered"))
        .join(RentalItem, RentalItem.product_id == Product.product_id)
        .group_by(Product.title)
        .order_by(func.count(RentalItem.product_id).desc())
        .limit(5)
        .all()
    )

    top_categories = (
        db.query(Category.name, func.count(RentalItem.product_id).label("ordered"))
        .join(Product, Product.category_id == Category.category_id)
        .join(RentalItem, RentalItem.product_id == Product.product_id)
        .group_by(Category.name)
        .order_by(func.count(RentalItem.product_id).desc())
        .limit(5)
        .all()
    )

    return {
        "kpi": {
            "rentals": rentals,
            "revenue": float(revenue),
        },
        "top_products": [{"title": t[0], "ordered": int(t[1])} for t in top_products],
        "top_categories": [{"name": t[0], "ordered": int(t[1])} for t in top_categories],
    }


