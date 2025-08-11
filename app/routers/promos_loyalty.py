from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.promotions import Promotion
from ..models.loyalty import LoyaltyAccount
from ..utils.auth import require_roles


router = APIRouter(prefix="/engage", tags=["promotions", "loyalty"])


class PromoCreate(BaseModel):
    code: str
    discount_type: str
    value: float
    valid_from: date
    valid_to: date


@router.post("/promotions", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_promo(payload: PromoCreate, db: Session = Depends(get_db), _: None = Depends(require_roles("Admin", "Seller"))):
    if db.query(Promotion).filter(Promotion.code == payload.code).first():
        raise HTTPException(status_code=400, detail="Promo code exists")
    promo = Promotion(code=payload.code, discount_type=payload.discount_type, value=payload.value, valid_from=payload.valid_from, valid_to=payload.valid_to)
    db.add(promo); db.commit(); db.refresh(promo)
    return {"promo_id": promo.promo_id}


@router.get("/promotions", response_model=list[dict])
def list_promos(db: Session = Depends(get_db)):
    promos = db.query(Promotion).all()
    return [{"promo_id": p.promo_id, "code": p.code, "value": float(p.value)} for p in promos]


class LoyaltyCreate(BaseModel):
    user_id: int


@router.post("/loyalty", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_loyalty(payload: LoyaltyCreate, db: Session = Depends(get_db)):
    acc = db.query(LoyaltyAccount).filter(LoyaltyAccount.user_id == payload.user_id).first()
    if acc:
        return {"account_id": acc.account_id}
    acc = LoyaltyAccount(user_id=payload.user_id, points_balance=0)
    db.add(acc); db.commit(); db.refresh(acc)
    return {"account_id": acc.account_id}


@router.post("/loyalty/{user_id}/earn", response_model=dict)
def earn_points(user_id: int, points: int = 10, db: Session = Depends(get_db)):
    acc = db.query(LoyaltyAccount).filter(LoyaltyAccount.user_id == user_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Loyalty account not found")
    acc.points_balance = int(acc.points_balance or 0) + points
    db.commit()
    return {"points_balance": acc.points_balance}


