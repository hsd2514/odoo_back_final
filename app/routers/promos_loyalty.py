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


class PromoApply(BaseModel):
    code: str
    cart_total: float


@router.post("/promotions/apply", response_model=dict)
def apply_promo(payload: PromoApply, db: Session = Depends(get_db)):
    """Apply a promotion code to a cart total"""
    from datetime import date
    
    # Find the promotion
    promo = db.query(Promotion).filter(Promotion.code == payload.code).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion code not found")
    
    # Check if promotion is valid (within date range)
    today = date.today()
    if today < promo.valid_from or today > promo.valid_to:
        raise HTTPException(status_code=400, detail="Promotion code has expired or is not yet valid")
    
    # Calculate discount - ensure proper type conversion
    if promo.discount_type == "percentage":
        # Convert Decimal to float for calculation
        promo_value = float(promo.value)
        cart_total = float(payload.cart_total)
        discount_amount = cart_total * (promo_value / 100)
    elif promo.discount_type == "fixed":
        # Convert Decimal to float for calculation
        discount_amount = float(promo.value)
    else:
        raise HTTPException(status_code=400, detail="Invalid discount type")
    
    # Ensure discount doesn't exceed cart total
    cart_total = float(payload.cart_total)
    discount_amount = min(discount_amount, cart_total)
    
    final_total = cart_total - discount_amount
    
    return {
        "promo_id": promo.promo_id,
        "code": promo.code,
        "discount_type": promo.discount_type,
        "discount_value": float(promo.value),
        "cart_total": float(payload.cart_total),
        "discount_amount": round(discount_amount, 2),
        "final_total": round(final_total, 2),
        "valid": True
    }


@router.post("/promotions/test-setup", response_model=dict)
def setup_test_promotions(db: Session = Depends(get_db)):
    """Setup test promotion codes for development"""
    from datetime import date, timedelta
    
    # Check if test promotions already exist
    existing = db.query(Promotion).filter(Promotion.code.in_(["WELCOME10", "SAVE20", "FIXED50"])).all()
    if existing:
        return {"message": "Test promotions already exist", "count": len(existing)}
    
    # Create test promotions
    today = date.today()
    test_promos = [
        {
            "code": "WELCOME10",
            "discount_type": "percentage",
            "value": 10.0,
            "valid_from": today,
            "valid_to": today + timedelta(days=365)
        },
        {
            "code": "SAVE20",
            "discount_type": "percentage", 
            "value": 20.0,
            "valid_from": today,
            "valid_to": today + timedelta(days=365)
        },
        {
            "code": "FIXED50",
            "discount_type": "fixed",
            "value": 50.0,
            "valid_from": today,
            "valid_to": today + timedelta(days=365)
        }
    ]
    
    for promo_data in test_promos:
        promo = Promotion(**promo_data)
        db.add(promo)
    
    db.commit()
    
    return {
        "message": "Test promotions created successfully",
        "promotions": ["WELCOME10", "SAVE20", "FIXED50"],
        "details": {
            "WELCOME10": "10% off",
            "SAVE20": "20% off", 
            "FIXED50": "₹50 off"
        }
    }


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


