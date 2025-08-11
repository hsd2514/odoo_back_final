from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.rentals import Notification, RentalOrder, RentalItem


router = APIRouter(prefix="/utility", tags=["utility"])


class NotificationCreate(BaseModel):
    user_id: int
    type: str
    scheduled_for: datetime | None = None
    payload: dict | None = None


@router.post("/notifications", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_notification(payload: NotificationCreate, db: Session = Depends(get_db)):
    n = Notification(user_id=payload.user_id, type=payload.type, scheduled_for=payload.scheduled_for, payload=payload.payload, status="scheduled")
    db.add(n); db.commit(); db.refresh(n)
    return {"notification_id": n.notification_id}


@router.post("/notifications/{notification_id}/mark_sent", response_model=dict)
def mark_sent(notification_id: int, db: Session = Depends(get_db)):
    n = db.query(Notification).get(notification_id)
    if not n:
        return {"updated": False}
    n.status = "sent"
    n.sent_at = datetime.utcnow()
    db.commit()
    return {"updated": True}


@router.get("/availability", response_model=list[dict])
def get_availability(product_id: int, from_ts: datetime, to_ts: datetime, db: Session = Depends(get_db)):
    orders = (
        db.query(RentalOrder)
        .join(RentalItem, RentalItem.rental_id == RentalOrder.rental_id)
        .filter(RentalItem.product_id == product_id)
        .filter(RentalOrder.end_ts >= from_ts, RentalOrder.start_ts <= to_ts)
        .all()
    )
    return [
        {"start": o.start_ts.isoformat(), "end": o.end_ts.isoformat(), "status": o.status}
        for o in orders
    ]


