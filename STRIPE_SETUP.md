# Stripe Payment Integration Guide

## Overview

This guide explains how to set up and use Stripe payment processing in your Odoo Rental System. Stripe provides secure, PCI-compliant payment processing with support for cards, wallets, and international payments.

## Features Implemented

### Payment Methods
- **Payment Intents**: For custom payment flows with Stripe Elements
- **Checkout Sessions**: For hosted checkout pages
- **Saved Payment Methods**: For returning customers
- **Refunds**: For processing returns and cancellations

### Security Features
- **Webhooks**: Real-time payment status updates
- **Authentication**: Role-based payment access
- **PCI Compliance**: Secure payment processing
- **Fraud Prevention**: Built-in Stripe fraud detection

## Stripe Account Setup

### 1. Create Stripe Account
1. Go to https://stripe.com and create an account
2. Complete account verification process
3. Access your Stripe Dashboard

### 2. Get API Keys
1. In Stripe Dashboard, go to **Developers** → **API keys**
2. Copy your **Publishable key** (starts with `pk_test_` or `pk_live_`)
3. Copy your **Secret key** (starts with `sk_test_` or `sk_live_`)

### 3. Set Up Webhooks (Optional but Recommended)
1. Go to **Developers** → **Webhooks**
2. Click **Add endpoint**
3. Set endpoint URL: `https://your-domain.com/payments/stripe/webhook`
4. Select events to listen to:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `checkout.session.completed`
5. Copy the **Webhook secret** (starts with `whsec_`)

## Environment Configuration

Add these variables to your `.env` file:

```env
# Stripe Payment Configuration
STRIPE_SECRET_KEY=sk_test_your_actual_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_actual_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_CURRENCY=usd
PAYMENT_SUCCESS_URL=http://localhost:3000/payment/success
PAYMENT_CANCEL_URL=http://localhost:3000/payment/cancel
```

### Test vs Live Keys
- **Test keys**: Use during development (`sk_test_`, `pk_test_`)
- **Live keys**: Use in production (`sk_live_`, `pk_live_`)

## API Endpoints

### 1. Get Stripe Configuration
```http
GET /payments/stripe/config
```
Returns publishable key and configuration for frontend.

### 2. Create Payment Intent
```http
POST /payments/stripe/payment-intent
Content-Type: application/json

{
    "rental_id": 123,
    "payment_method_id": "pm_1234567890",  // optional
    "save_payment_method": false,           // optional
    "return_url": "https://your-app.com/return"  // optional
}
```

### 3. Create Checkout Session
```http
POST /payments/stripe/checkout-session
Content-Type: application/json

{
    "rental_id": 123,
    "success_url": "https://your-app.com/success",  // optional
    "cancel_url": "https://your-app.com/cancel"     // optional
}
```

### 4. Get Payment Status
```http
GET /payments/stripe/payment-status/{payment_intent_id}
```

### 5. Process Refund (Admin/Staff only)
```http
POST /payments/stripe/refund
Content-Type: application/json

{
    "payment_intent_id": "pi_1234567890",
    "amount": 2000,  // optional, in cents
    "reason": "Customer request"  // optional
}
```

## Frontend Integration

### Payment Intent Flow (Stripe Elements)

```javascript
// 1. Get Stripe configuration
const configResponse = await fetch('/payments/stripe/config');
const config = await configResponse.json();

// 2. Initialize Stripe
const stripe = Stripe(config.publishable_key);

// 3. Create Payment Intent
const paymentResponse = await fetch('/payments/stripe/payment-intent', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify({
        rental_id: rentalId
    })
});

const { client_secret } = await paymentResponse.json();

// 4. Create Elements
const elements = stripe.elements();
const cardElement = elements.create('card');
cardElement.mount('#card-element');

// 5. Confirm Payment
const { error, paymentIntent } = await stripe.confirmCardPayment(client_secret, {
    payment_method: {
        card: cardElement,
        billing_details: {
            name: 'Customer Name',
            email: 'customer@example.com'
        }
    }
});

if (error) {
    console.error('Payment failed:', error);
} else {
    console.log('Payment succeeded:', paymentIntent);
}
```

### Checkout Session Flow (Hosted Checkout)

```javascript
// 1. Create Checkout Session
const checkoutResponse = await fetch('/payments/stripe/checkout-session', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify({
        rental_id: rentalId,
        success_url: 'https://your-app.com/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url: 'https://your-app.com/cancel'
    })
});

const { checkout_url } = await checkoutResponse.json();

// 2. Redirect to Stripe Checkout
window.location.href = checkout_url;
```

## Testing

### Test Card Numbers
Use these test card numbers during development:

| Card Number | Brand | Description |
|-------------|-------|-------------|
| 4242424242424242 | Visa | Succeeds |
| 4000000000000002 | Visa | Declined |
| 4000000000009995 | Visa | Insufficient funds |
| 5555555555554444 | Mastercard | Succeeds |
| 378282246310005 | American Express | Succeeds |

### Test Values
- **CVC**: Any 3-digit number (4-digit for Amex)
- **Expiry**: Any future date
- **Postal Code**: Any valid postal code

### Testing Webhooks
1. Use Stripe CLI for local testing:
```bash
stripe listen --forward-to localhost:8000/payments/stripe/webhook
```

2. Test webhook events:
```bash
stripe trigger payment_intent.succeeded
```

## Error Handling

### Common Errors
- **Invalid API Key**: Check your secret key
- **Payment Failed**: Use test card numbers
- **Webhook Signature**: Verify webhook secret
- **Amount Too Small**: Minimum $0.50 USD

### Error Responses
```json
{
    "detail": "Failed to create payment intent: Your card was declined."
}
```

## Security Best Practices

### API Keys
- Never expose secret keys in frontend code
- Use environment variables for all keys
- Rotate keys regularly in production

### Webhooks
- Always verify webhook signatures
- Use HTTPS endpoints only
- Handle duplicate events idempotently

### Payment Flow
- Validate amounts server-side
- Check user authorization
- Log all payment events

## Production Deployment

### 1. Switch to Live Keys
Replace test keys with live keys in your production environment.

### 2. Set Up Webhooks
Configure webhook endpoints for your production domain.

### 3. Enable Additional Features
- Radar (fraud prevention)
- 3D Secure (SCA compliance)
- Saved payment methods

### 4. Monitor Payments
- Set up Stripe Dashboard alerts
- Monitor payment success rates
- Review failed payments regularly

## Troubleshooting

### Payment Intent Creation Fails
- Check rental order exists and status
- Verify user authorization
- Ensure amount is valid (>= $0.50)

### Webhook Not Received
- Check webhook URL is accessible
- Verify webhook secret is correct
- Check Stripe Dashboard webhook logs

### Frontend Payment Fails
- Verify publishable key is correct
- Check browser console for errors
- Test with different card numbers

## Advanced Features

### Saved Payment Methods
```javascript
// Save payment method during payment
const { client_secret } = await createPaymentIntent({
    rental_id: 123,
    save_payment_method: true
});
```

### Customer Portal
- View saved payment methods
- Update billing information
- Download payment receipts

### Subscriptions (Future)
- Recurring rental payments
- Membership plans
- Usage-based billing

## Support

### Documentation
- [Stripe API Documentation](https://stripe.com/docs/api)
- [Stripe Elements Guide](https://stripe.com/docs/stripe-js)
- [Webhook Guide](https://stripe.com/docs/webhooks)

### Testing Tools
- [Stripe CLI](https://stripe.com/docs/stripe-cli)
- [Webhook Testing](https://stripe.com/docs/webhooks/test)
- [Test Cards](https://stripe.com/docs/testing)

Your Stripe payment integration is now ready for secure, PCI-compliant payment processing! 🎉
