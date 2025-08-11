from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.rentals import Schedule
from ..utils.auth import require_roles


router = APIRouter(prefix="/schedules", tags=["schedules"])


class ScheduleCreate(BaseModel):
    rental_id: int
    type: str = Field(..., description="pickup or return")
    scheduled_for: datetime


class ScheduleUpdate(BaseModel):
    actual_at: datetime


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
    summary="Create pickup/return schedule",
)
def create_schedule(
    payload: ScheduleCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin", "Seller")),
):
    sched = Schedule(
        rental_id=payload.rental_id,
        type=payload.type,
        scheduled_for=payload.scheduled_for,
    )
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return {"schedule_id": sched.schedule_id}


@router.patch(
    "/{schedule_id}",
    response_model=dict,
    summary="Mark schedule actual time",
)
def patch_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_roles("Admin", "Seller")),
):
    sched = db.query(Schedule).get(schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")
    sched.actual_at = payload.actual_at
    db.commit()
    return {"updated": True}


