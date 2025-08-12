from __future__ import annotations

from datetime import datetime
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.rentals import RentalOrder
from ..models.rentals import HandoverQR
from ..utils.auth import require_roles, get_current_user


router = APIRouter(prefix="/handover_qr", tags=["handover_qr"])


class QRCreate(BaseModel):
    rental_id: int
    type: str = Field(..., description="pickup or return")


class QRVerify(BaseModel):
    qr_token: str


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def issue_qr(payload: QRCreate, db: Session = Depends(get_db), _: None = Depends(require_roles("Admin", "Seller"))):
    qr = HandoverQR(rental_id=payload.rental_id, type=payload.type, qr_token=token_urlsafe(24))
    db.add(qr); db.commit(); db.refresh(qr)
    return {"qr_id": qr.qr_id, "qr_token": qr.qr_token}


@router.post("/verify", response_model=dict)
def verify_qr(payload: QRVerify, db: Session = Depends(get_db), current=Depends(get_current_user)):
    qr = db.query(HandoverQR).filter(HandoverQR.qr_token == payload.qr_token).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR token not found")
    if qr.verified_at:
        raise HTTPException(status_code=409, detail="QR already verified")
    qr.verified_by = current.user_id
    qr.verified_at = datetime.utcnow()
    # Update the related order status
    order = db.query(RentalOrder).filter(RentalOrder.rental_id == qr.rental_id).first()
    if order:
        # If the renting user scans, mark as 'rented' (picked up)
        if current.user_id == order.customer_id:
            order.status = 'rented'
        else:
            # Staff/Seller flow: pickup -> active, return -> returned
            if qr.type == 'pickup':
                order.status = 'rented'
            elif qr.type == 'return':
                order.status = 'returned'
    db.commit()
    return {"verified": True, "order_status": order.status if order else None}


