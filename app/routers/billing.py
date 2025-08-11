from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.billing import Invoice, Payment
from ..models.rentals import RentalOrder
from ..utils.auth import require_roles, get_current_user, user_has_any_role


router = APIRouter(prefix="/billing", tags=["billing"])


class InvoiceCreate(BaseModel):
    rental_id: int
    amount_due: float | None = None


@router.post("/invoices", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db), _: None = Depends(require_roles("Admin", "Seller"))):
    order = db.query(RentalOrder).get(payload.rental_id)
    if not order:
        raise HTTPException(status_code=404, detail="Rental order not found")
    inv = Invoice(rental_id=payload.rental_id, amount_due=payload.amount_due or order.total_amount, amount_paid=0, status="unpaid")
    db.add(inv); db.commit(); db.refresh(inv)
    return {"invoice_id": inv.invoice_id}


class PaymentCreate(BaseModel):
    rental_id: int
    invoice_id: int | None = None
    amount: float
    gateway: str | None = None


@router.post("/payments", response_model=dict, status_code=status.HTTP_201_CREATED)
def record_payment(payload: PaymentCreate, db: Session = Depends(get_db), current=Depends(get_current_user)):
    inv = db.query(Invoice).get(payload.invoice_id) if payload.invoice_id else db.query(Invoice).filter(Invoice.rental_id == payload.rental_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    # Authorization: order owner or Admin/Seller
    order = db.query(RentalOrder).get(inv.rental_id)
    if not (order and (order.customer_id == current.user_id or user_has_any_role(db, current.user_id, ["Admin", "Seller"]))):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    inv.amount_paid = float(inv.amount_paid or 0) + payload.amount
    if inv.amount_paid >= inv.amount_due:
        inv.status = "paid"
        if order:
            order.status = "completed"
    db.add(Payment(rental_id=payload.rental_id, invoice_id=inv.invoice_id, gateway=payload.gateway, amount=payload.amount))
    db.commit()
    return {"paid": True, "invoice_status": inv.status}


