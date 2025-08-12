from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models.user import User
from ..models.rentals import RentalOrder
from ..schemas.payments import (
    StripePaymentIntentCreate, StripePaymentIntentResponse,
    StripeCheckoutSessionCreate, StripeCheckoutSessionResponse,
    StripePaymentStatusResponse, StripeRefundRequest, StripeRefundResponse,
    StripeCustomerResponse, StripeConfigResponse, PaymentSummary,
    StripePaymentConfirmation
)
from ..services.stripe_service import stripe_service
from ..utils.auth import get_current_user, require_roles


router = APIRouter(prefix="/payments/stripe", tags=["stripe-payments"])


@router.get("/config",
           response_model=StripeConfigResponse,
           summary="Get Stripe configuration",
           description="Get Stripe publishable key and configuration for frontend")
async def get_stripe_config():
    """
    Get Stripe configuration for frontend integration.
    
    Returns publishable key and other configuration needed by the frontend
    to initialize Stripe Elements or Checkout.
    """
    from ..config import get_settings
    settings = get_settings()
    
    if not settings.stripe_publishable_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured"
        )
    
    return StripeConfigResponse(
        publishable_key=settings.stripe_publishable_key,
        currency=settings.stripe_currency,
        country="US"
    )


@router.post("/payment-intent",
            response_model=StripePaymentIntentResponse,
            status_code=status.HTTP_201_CREATED,
            summary="Create Payment Intent",
            description="Create a Stripe Payment Intent for rental payment")
async def create_payment_intent(
    payment_data: StripePaymentIntentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Payment Intent for rental payment.
    
    This creates a payment intent that can be used with Stripe Elements
    for secure payment processing on the frontend.
    """
    # Get rental order
    rental_order = db.query(RentalOrder).filter(
        RentalOrder.rental_id == payment_data.rental_id
    ).first()
    
    if not rental_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rental order not found"
        )
    
    # Check if user owns the rental or is admin/staff
    if rental_order.customer_id != current_user.user_id:
        # Check if user has admin/staff role
        from ..utils.auth import user_has_any_role
        if not user_has_any_role(db, current_user.user_id, ["admin", "staff"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to process payment for this rental"
            )
    
    # Check if rental can be paid
    if rental_order.status not in ['pending_payment', 'confirmed']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot process payment for rental in status: {rental_order.status}"
        )
    
    try:
        # Get or create Stripe customer
        customer_id = await stripe_service.get_or_create_customer(current_user)
        
        # Create payment intent
        payment_intent = await stripe_service.create_payment_intent(
            rental_order=rental_order,
            customer_id=customer_id,
            payment_method_id=payment_data.payment_method_id,
            save_payment_method=payment_data.save_payment_method
        )
        
        return StripePaymentIntentResponse(
            client_secret=payment_intent.client_secret,
            payment_intent_id=payment_intent.id,
            amount=payment_intent.amount,
            currency=payment_intent.currency,
            status=payment_intent.status,
            rental_id=payment_data.rental_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment intent: {str(e)}"
        )


@router.post("/checkout-session",
            response_model=StripeCheckoutSessionResponse,
            status_code=status.HTTP_201_CREATED,
            summary="Create Checkout Session",
            description="Create a Stripe Checkout Session for rental payment")
async def create_checkout_session(
    checkout_data: StripeCheckoutSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Checkout Session for rental payment.
    
    This creates a hosted checkout page that handles the entire payment flow.
    """
    # Get rental order
    rental_order = db.query(RentalOrder).filter(
        RentalOrder.rental_id == checkout_data.rental_id
    ).first()
    
    if not rental_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rental order not found"
        )
    
    # Check authorization
    if rental_order.customer_id != current_user.user_id:
        from ..utils.auth import user_has_any_role
        if not user_has_any_role(db, current_user.user_id, ["admin", "staff"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to process payment for this rental"
            )
    
    try:
        # Get or create Stripe customer
        customer_id = await stripe_service.get_or_create_customer(current_user)
        
        # Create checkout session
        session = await stripe_service.create_checkout_session(
            rental_order=rental_order,
            customer_id=customer_id,
            success_url=checkout_data.success_url,
            cancel_url=checkout_data.cancel_url
        )
        
        return StripeCheckoutSessionResponse(
            checkout_url=session.url,
            session_id=session.id,
            rental_id=checkout_data.rental_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}"
        )


@router.post("/confirm-payment",
            status_code=status.HTTP_200_OK,
            summary="Confirm Payment",
            description="Confirm a payment intent")
async def confirm_payment(
    confirmation: StripePaymentConfirmation,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Confirm a payment intent after frontend handles the payment.
    """
    try:
        payment_intent = await stripe_service.confirm_payment_intent(
            confirmation.payment_intent_id
        )

        # Persist success to DB even when webhooks are not configured
        if getattr(payment_intent, 'status', None) == 'succeeded':
            await stripe_service._handle_payment_success(payment_intent, db)  # type: ignore[attr-defined]
        
        return {
            "message": "Payment confirmed successfully",
            "status": payment_intent.status,
            "payment_intent_id": payment_intent.id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm payment: {str(e)}"
        )


@router.get("/payment-status/{payment_intent_id}",
           response_model=StripePaymentStatusResponse,
           summary="Get Payment Status",
           description="Get the status of a payment intent")
async def get_payment_status(
    payment_intent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the current status of a payment intent.
    """
    try:
        payment_intent = await stripe_service.get_payment_intent(payment_intent_id)
        
        # Check if user is authorized to view this payment
        rental_id = payment_intent.metadata.get('rental_id')
        if rental_id:
            rental_order = db.query(RentalOrder).filter(
                RentalOrder.rental_id == int(rental_id)
            ).first()
            
            if rental_order and rental_order.customer_id != current_user.user_id:
                from ..utils.auth import user_has_any_role
                if not user_has_any_role(db, current_user.user_id, ["admin", "staff"]):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not authorized to view this payment"
                    )
        
        return StripePaymentStatusResponse(
            payment_intent_id=payment_intent.id,
            status=payment_intent.status,
            amount=payment_intent.amount,
            currency=payment_intent.currency,
            rental_id=int(rental_id) if rental_id else 0,
            created_at=str(payment_intent.created),
            updated_at=str(payment_intent.created)  # Stripe doesn't have updated_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment status: {str(e)}"
        )


@router.post("/refund",
            response_model=StripeRefundResponse,
            summary="Process Refund",
            description="Process a refund for a payment")
async def process_refund(
    refund_data: StripeRefundRequest,
    current_user: User = Depends(require_roles("admin", "staff")),
    db: Session = Depends(get_db)
):
    """
    Process a refund for a payment. Requires admin or staff role.
    """
    try:
        refund = await stripe_service.create_refund(
            payment_intent_id=refund_data.payment_intent_id,
            amount=refund_data.amount,
            reason=refund_data.reason
        )
        
        return StripeRefundResponse(
            refund_id=refund.id,
            amount=refund.amount,
            currency=refund.currency,
            status=refund.status,
            reason=refund.reason
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process refund: {str(e)}"
        )


@router.get("/customer",
           response_model=StripeCustomerResponse,
           summary="Get Customer Info",
           description="Get Stripe customer information and saved payment methods")
async def get_customer_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Stripe customer information including saved payment methods.
    """
    try:
        customer_id = await stripe_service.get_or_create_customer(current_user)
        payment_methods = await stripe_service.get_customer_payment_methods(customer_id)
        
        return StripeCustomerResponse(
            customer_id=customer_id,
            email=current_user.email,
            name=current_user.full_name,
            payment_methods=[
                {
                    "payment_method_id": pm.id,
                    "type": pm.type,
                    "last4": pm.card.last4 if pm.card else None,
                    "brand": pm.card.brand if pm.card else None,
                    "exp_month": pm.card.exp_month if pm.card else None,
                    "exp_year": pm.card.exp_year if pm.card else None,
                }
                for pm in payment_methods
            ]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get customer info: {str(e)}"
        )


@router.get("/rental/{rental_id}/summary",
           response_model=PaymentSummary,
           summary="Get Payment Summary",
           description="Get payment summary for a rental order")
async def get_payment_summary(
    rental_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get payment summary for a rental order.
    """
    rental_order = db.query(RentalOrder).filter(
        RentalOrder.rental_id == rental_id
    ).first()
    
    if not rental_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rental order not found"
        )
    
    # Check authorization
    if rental_order.customer_id != current_user.user_id:
        from ..utils.auth import user_has_any_role
        if not user_has_any_role(db, current_user.user_id, ["admin", "staff"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this rental"
            )
    
    can_pay = rental_order.status in ['pending_payment', 'confirmed']
    amount_cents = stripe_service.dollars_to_cents(float(rental_order.total_amount))
    
    return PaymentSummary(
        rental_id=rental_id,
        total_amount=float(rental_order.total_amount),
        amount_in_cents=amount_cents,
        currency=stripe_service.settings.stripe_currency,
        payment_status=rental_order.status,
        can_pay=can_pay,
        payment_url=f"/payments/stripe/checkout-session" if can_pay else None
    )


@router.post("/webhook",
            status_code=status.HTTP_200_OK,
            summary="Stripe Webhook",
            description="Handle Stripe webhook events")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Stripe webhook events.
    
    This endpoint receives and processes webhook events from Stripe
    to update payment statuses and handle various payment events.
    """
    try:
        payload = await request.body()
        signature = request.headers.get('stripe-signature')
        
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe signature"
            )
        
        # Verify webhook signature
        event = stripe_service.verify_webhook_signature(payload, signature)
        
        # Handle the event
        success = await stripe_service.handle_webhook_event(event, db)
        
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process webhook event"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook error: {str(e)}"
        )
