from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

from pydantic import Field, validator

from .common import BaseSchema


class PaymentBase(BaseSchema):
    invoice_id: int | None = None
    rental_id: int
    gateway: str | None = None
    txn_id: str | None = None
    amount: float
    paid_at: datetime | None = None


class PaymentCreate(PaymentBase):
    pass


class PaymentRead(PaymentBase):
    payment_id: int


# Stripe-specific schemas
class StripePaymentIntentCreate(BaseSchema):
    """Schema for creating a Stripe Payment Intent"""
    rental_id: int = Field(..., description="Rental order ID to process payment for")
    payment_method_id: Optional[str] = Field(None, description="Stripe Payment Method ID for immediate payment")
    save_payment_method: bool = Field(False, description="Whether to save payment method for future use")
    return_url: Optional[str] = Field(None, description="URL to redirect after payment completion")


class StripePaymentIntentResponse(BaseSchema):
    """Response schema for Payment Intent creation"""
    client_secret: str = Field(..., description="Client secret for frontend payment confirmation")
    payment_intent_id: str = Field(..., description="Stripe Payment Intent ID")
    amount: int = Field(..., description="Payment amount in cents")
    currency: str = Field(..., description="Payment currency")
    status: str = Field(..., description="Payment Intent status")
    rental_id: int = Field(..., description="Associated rental order ID")


class StripeCheckoutSessionCreate(BaseSchema):
    """Schema for creating a Stripe Checkout Session"""
    rental_id: int = Field(..., description="Rental order ID to process payment for")
    success_url: Optional[str] = Field(None, description="URL to redirect after successful payment")
    cancel_url: Optional[str] = Field(None, description="URL to redirect after cancelled payment")
    collect_shipping_address: bool = Field(False, description="Whether to collect shipping address")


class StripeCheckoutSessionResponse(BaseSchema):
    """Response schema for Checkout Session creation"""
    checkout_url: str = Field(..., description="Stripe Checkout URL to redirect user")
    session_id: str = Field(..., description="Stripe Checkout Session ID")
    rental_id: int = Field(..., description="Associated rental order ID")


class StripePaymentMethodResponse(BaseSchema):
    """Response schema for payment method operations"""
    payment_method_id: str = Field(..., description="Stripe Payment Method ID")
    type: str = Field(..., description="Payment method type")
    last4: Optional[str] = Field(None, description="Last 4 digits of card")
    brand: Optional[str] = Field(None, description="Card brand (visa, mastercard, etc.)")
    exp_month: Optional[int] = Field(None, description="Card expiration month")
    exp_year: Optional[int] = Field(None, description="Card expiration year")


class StripeWebhookEvent(BaseSchema):
    """Schema for Stripe webhook events"""
    event_type: str = Field(..., description="Stripe event type")
    event_id: str = Field(..., description="Stripe event ID")
    data: Dict[str, Any] = Field(..., description="Event data")


class StripePaymentConfirmation(BaseSchema):
    """Schema for payment confirmation"""
    payment_intent_id: str = Field(..., description="Stripe Payment Intent ID")
    payment_method_id: Optional[str] = Field(None, description="Payment method used")


class StripePaymentStatusResponse(BaseSchema):
    """Response schema for payment status queries"""
    payment_intent_id: str = Field(..., description="Stripe Payment Intent ID")
    status: str = Field(..., description="Payment status")
    amount: int = Field(..., description="Payment amount in cents")
    currency: str = Field(..., description="Payment currency")
    rental_id: int = Field(..., description="Associated rental order ID")
    payment_method: Optional[StripePaymentMethodResponse] = Field(None, description="Payment method details")
    created_at: str = Field(..., description="Payment creation timestamp")
    updated_at: str = Field(..., description="Payment last update timestamp")


class StripeRefundRequest(BaseSchema):
    """Schema for processing refunds"""
    payment_intent_id: str = Field(..., description="Stripe Payment Intent ID to refund")
    amount: Optional[int] = Field(None, description="Refund amount in cents (full refund if not specified)")
    reason: Optional[str] = Field(None, description="Reason for refund")


class StripeRefundResponse(BaseSchema):
    """Response schema for refund operations"""
    refund_id: str = Field(..., description="Stripe Refund ID")
    amount: int = Field(..., description="Refunded amount in cents")
    currency: str = Field(..., description="Refund currency")
    status: str = Field(..., description="Refund status")
    reason: Optional[str] = Field(None, description="Refund reason")


class StripeCustomerResponse(BaseSchema):
    """Response schema for customer operations"""
    customer_id: str = Field(..., description="Stripe Customer ID")
    email: str = Field(..., description="Customer email")
    name: Optional[str] = Field(None, description="Customer name")
    default_payment_method: Optional[str] = Field(None, description="Default payment method ID")
    payment_methods: List[StripePaymentMethodResponse] = Field(default=[], description="Available payment methods")


class StripeConfigResponse(BaseSchema):
    """Response schema for Stripe configuration"""
    publishable_key: str = Field(..., description="Stripe publishable key for frontend")
    currency: str = Field(..., description="Default currency")
    country: str = Field("US", description="Country code")


class PaymentSummary(BaseSchema):
    """Summary of payment-related information for a rental"""
    rental_id: int = Field(..., description="Rental order ID")
    total_amount: float = Field(..., description="Total rental amount")
    amount_in_cents: int = Field(..., description="Amount in cents for Stripe")
    currency: str = Field(..., description="Payment currency")
    payment_status: str = Field(..., description="Current payment status")
    payment_intent_id: Optional[str] = Field(None, description="Stripe Payment Intent ID if exists")
    can_pay: bool = Field(..., description="Whether payment can be processed")
    payment_url: Optional[str] = Field(None, description="Payment URL if available")


