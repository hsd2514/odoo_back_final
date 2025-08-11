from __future__ import annotations

import stripe
from typing import Optional, Dict, Any, List
from decimal import Decimal
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.rentals import RentalOrder
from ..models.billing import Payment
from ..models.user import User


class StripeService:
    def __init__(self):
        self.settings = get_settings()
        stripe.api_key = self.settings.stripe_secret_key
    
    def dollars_to_cents(self, amount: float) -> int:
        """Convert dollar amount to cents for Stripe"""
        return int(amount * 100)
    
    def cents_to_dollars(self, amount: int) -> float:
        """Convert cents to dollar amount"""
        return amount / 100
    
    async def create_customer(self, user: User) -> str:
        """Create a Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.full_name,
                phone=user.phone,
                metadata={
                    'user_id': str(user.user_id),
                    'internal_id': str(user.user_id)
                }
            )
            return customer.id
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create Stripe customer: {str(e)}")
    
    async def get_or_create_customer(self, user: User) -> str:
        """Get existing customer or create new one"""
        try:
            # Try to find existing customer by email
            customers = stripe.Customer.list(email=user.email, limit=1)
            if customers.data:
                return customers.data[0].id
            
            # Create new customer if not found
            return await self.create_customer(user)
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to get or create customer: {str(e)}")
    
    async def create_payment_intent(
        self, 
        rental_order: RentalOrder, 
        customer_id: str,
        payment_method_id: Optional[str] = None,
        save_payment_method: bool = False
    ) -> Dict[str, Any]:
        """Create a Stripe Payment Intent"""
        try:
            amount_cents = self.dollars_to_cents(float(rental_order.total_amount))
            
            intent_data = {
                'amount': amount_cents,
                'currency': self.settings.stripe_currency,
                'customer': customer_id,
                'metadata': {
                    'rental_id': str(rental_order.rental_id),
                    'customer_id': str(rental_order.customer_id),
                    'order_type': 'rental'
                },
                'description': f'Rental payment for order #{rental_order.rental_id}',
            }
            
            if payment_method_id:
                intent_data['payment_method'] = payment_method_id
                intent_data['confirm'] = True
                intent_data['return_url'] = self.settings.payment_success_url
            
            if save_payment_method:
                intent_data['setup_future_usage'] = 'on_session'
            
            payment_intent = stripe.PaymentIntent.create(**intent_data)
            return payment_intent
            
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create payment intent: {str(e)}")
    
    async def create_checkout_session(
        self,
        rental_order: RentalOrder,
        customer_id: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout Session"""
        try:
            amount_cents = self.dollars_to_cents(float(rental_order.total_amount))
            
            session_data = {
                'customer': customer_id,
                'payment_method_types': ['card'],
                'line_items': [{
                    'price_data': {
                        'currency': self.settings.stripe_currency,
                        'product_data': {
                            'name': f'Rental Order #{rental_order.rental_id}',
                            'description': f'Rental from {rental_order.start_ts} to {rental_order.end_ts}',
                        },
                        'unit_amount': amount_cents,
                    },
                    'quantity': 1,
                }],
                'mode': 'payment',
                'success_url': success_url or self.settings.payment_success_url + f'?session_id={{CHECKOUT_SESSION_ID}}',
                'cancel_url': cancel_url or self.settings.payment_cancel_url,
                'metadata': {
                    'rental_id': str(rental_order.rental_id),
                    'customer_id': str(rental_order.customer_id),
                    'order_type': 'rental'
                }
            }
            
            session = stripe.checkout.Session.create(**session_data)
            return session
            
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create checkout session: {str(e)}")
    
    async def confirm_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        """Confirm a payment intent"""
        try:
            payment_intent = stripe.PaymentIntent.confirm(payment_intent_id)
            return payment_intent
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to confirm payment intent: {str(e)}")
    
    async def get_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        """Get payment intent details"""
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return payment_intent
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to retrieve payment intent: {str(e)}")
    
    async def get_checkout_session(self, session_id: str) -> Dict[str, Any]:
        """Get checkout session details"""
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return session
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to retrieve checkout session: {str(e)}")
    
    async def create_refund(
        self,
        payment_intent_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a refund for a payment"""
        try:
            refund_data = {
                'payment_intent': payment_intent_id,
            }
            
            if amount:
                refund_data['amount'] = amount
            
            if reason:
                refund_data['reason'] = reason
                refund_data['metadata'] = {'reason': reason}
            
            refund = stripe.Refund.create(**refund_data)
            return refund
            
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create refund: {str(e)}")
    
    async def get_customer_payment_methods(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get customer's saved payment methods"""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type='card'
            )
            return payment_methods.data
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to get payment methods: {str(e)}")
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Verify Stripe webhook signature"""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.settings.stripe_webhook_secret
            )
            return event
        except ValueError:
            raise Exception("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise Exception("Invalid signature")
    
    async def handle_webhook_event(self, event: Dict[str, Any], db: Session) -> bool:
        """Handle Stripe webhook events"""
        try:
            event_type = event['type']
            event_data = event['data']['object']
            
            if event_type == 'payment_intent.succeeded':
                await self._handle_payment_success(event_data, db)
            elif event_type == 'payment_intent.payment_failed':
                await self._handle_payment_failed(event_data, db)
            elif event_type == 'checkout.session.completed':
                await self._handle_checkout_completed(event_data, db)
            
            return True
            
        except Exception as e:
            print(f"Error handling webhook event: {str(e)}")
            return False
    
    async def _handle_payment_success(self, payment_intent: Dict[str, Any], db: Session):
        """Handle successful payment"""
        rental_id = payment_intent.get('metadata', {}).get('rental_id')
        if not rental_id:
            return
        
        # Update payment record in database
        payment = Payment(
            rental_id=int(rental_id),
            gateway='stripe',
            txn_id=payment_intent['id'],
            amount=self.cents_to_dollars(payment_intent['amount']),
            paid_at=payment_intent.get('created')
        )
        
        db.add(payment)
        
        # Update rental order status if needed
        rental_order = db.query(RentalOrder).filter(
            RentalOrder.rental_id == int(rental_id)
        ).first()
        
        if rental_order and rental_order.status == 'pending_payment':
            rental_order.status = 'confirmed'
        
        db.commit()
    
    async def _handle_payment_failed(self, payment_intent: Dict[str, Any], db: Session):
        """Handle failed payment"""
        rental_id = payment_intent.get('metadata', {}).get('rental_id')
        if not rental_id:
            return
        
        # Update rental order status
        rental_order = db.query(RentalOrder).filter(
            RentalOrder.rental_id == int(rental_id)
        ).first()
        
        if rental_order:
            rental_order.status = 'payment_failed'
            db.commit()
    
    async def _handle_checkout_completed(self, session: Dict[str, Any], db: Session):
        """Handle completed checkout session"""
        rental_id = session.get('metadata', {}).get('rental_id')
        if not rental_id:
            return
        
        # Get payment intent from session
        payment_intent_id = session.get('payment_intent')
        if payment_intent_id:
            payment_intent = await self.get_payment_intent(payment_intent_id)
            await self._handle_payment_success(payment_intent, db)


# Singleton instance
stripe_service = StripeService()
