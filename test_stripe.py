#!/usr/bin/env python3
"""
Test script for Stripe payment integration
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

import httpx


async def test_stripe_integration():
    """Test the complete Stripe payment flow"""
    base_url = "http://localhost:8000"
    
    # Test data
    test_rental_id = 1  # Assuming a rental exists
    
    async with httpx.AsyncClient() as client:
        print("=== Testing Stripe Payment Integration ===\n")
        
        # Step 1: Get Stripe configuration
        print("1. Getting Stripe configuration...")
        config_response = await client.get(f"{base_url}/payments/stripe/config")
        
        print(f"   Status: {config_response.status_code}")
        if config_response.status_code == 200:
            config = config_response.json()
            print(f"   ✅ Stripe config retrieved")
            print(f"   Publishable Key: {config['publishable_key'][:20]}...")
            print(f"   Currency: {config['currency']}")
        else:
            print(f"   ❌ Failed to get Stripe config: {config_response.text}")
            return
        
        # Note: For the following tests, you need to be authenticated
        print("\n2. Note: The following tests require authentication:")
        print("   - Create a user account and get an access token")
        print("   - Include the token in Authorization header")
        print("   - Make sure a rental order exists in the database")
        
        # Example of what the authenticated flow would look like
        print("\n3. Example authenticated flow:")
        print("   a) Create Payment Intent:")
        print("      POST /payments/stripe/payment-intent")
        print("      {\"rental_id\": 1}")
        print("   ")
        print("   b) Create Checkout Session:")
        print("      POST /payments/stripe/checkout-session")
        print("      {\"rental_id\": 1}")
        print("   ")
        print("   c) Get Payment Status:")
        print("      GET /payments/stripe/payment-status/{payment_intent_id}")


def test_stripe_configuration():
    """Test Stripe configuration and service"""
    print("=== Testing Stripe Configuration ===\n")
    
    try:
        from app.config import get_settings
        from app.services.stripe_service import stripe_service
        
        settings = get_settings()
        
        print("Stripe Configuration:")
        print(f"   Secret Key: {'*' * 20 if settings.stripe_secret_key else 'Not configured'}")
        print(f"   Publishable Key: {'*' * 20 if settings.stripe_publishable_key else 'Not configured'}")
        print(f"   Webhook Secret: {'*' * 20 if settings.stripe_webhook_secret else 'Not configured'}")
        print(f"   Currency: {settings.stripe_currency}")
        print(f"   Success URL: {settings.payment_success_url}")
        print(f"   Cancel URL: {settings.payment_cancel_url}")
        
        if not settings.stripe_secret_key or not settings.stripe_publishable_key:
            print("\n⚠️  Stripe not configured")
            print("   Follow these steps:")
            print("   1. Create a Stripe account at https://stripe.com")
            print("   2. Get your API keys from Stripe Dashboard → Developers → API keys")
            print("   3. Set STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY in your .env file")
            print("   4. See STRIPE_SETUP.md for detailed instructions")
        else:
            print("\n✅ Stripe configuration looks good")
            
            # Test amount conversion
            print("\n=== Testing Amount Conversion ===")
            test_amount = 25.99
            cents = stripe_service.dollars_to_cents(test_amount)
            dollars = stripe_service.cents_to_dollars(cents)
            print(f"   ${test_amount} → {cents} cents → ${dollars}")
            
            if dollars == test_amount:
                print("   ✅ Amount conversion working correctly")
            else:
                print("   ❌ Amount conversion failed")
    
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure Stripe is installed: pip install stripe")
    except Exception as e:
        print(f"❌ Configuration error: {e}")


def print_stripe_test_cards():
    """Print Stripe test card information"""
    print("=== Stripe Test Cards ===\n")
    
    test_cards = [
        ("4242424242424242", "Visa", "✅ Succeeds"),
        ("4000000000000002", "Visa", "❌ Declined"),
        ("4000000000009995", "Visa", "❌ Insufficient funds"),
        ("5555555555554444", "Mastercard", "✅ Succeeds"),
        ("378282246310005", "American Express", "✅ Succeeds"),
        ("4000000000000069", "Visa", "❌ Expired card"),
        ("4000000000000127", "Visa", "❌ Incorrect CVC"),
    ]
    
    print("Use these test cards during development:")
    print(f"{'Card Number':<20} {'Brand':<15} {'Result'}")
    print("-" * 50)
    
    for card_number, brand, result in test_cards:
        print(f"{card_number:<20} {brand:<15} {result}")
    
    print("\nAdditional test info:")
    print("   CVC: Any 3-digit number (4-digit for Amex)")
    print("   Expiry: Any future date")
    print("   Postal Code: Any valid postal code")


def print_frontend_examples():
    """Print frontend integration examples"""
    print("=== Frontend Integration Examples ===\n")
    
    print("1. Payment Intent with Stripe Elements:")
    print("""
// Get Stripe configuration
const config = await fetch('/payments/stripe/config').then(r => r.json());
const stripe = Stripe(config.publishable_key);

// Create Payment Intent
const paymentResponse = await fetch('/payments/stripe/payment-intent', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + accessToken
    },
    body: JSON.stringify({ rental_id: 123 })
});

const { client_secret } = await paymentResponse.json();

// Create and mount card element
const elements = stripe.elements();
const cardElement = elements.create('card');
cardElement.mount('#card-element');

// Confirm payment
const { error, paymentIntent } = await stripe.confirmCardPayment(client_secret, {
    payment_method: {
        card: cardElement,
        billing_details: { name: 'Customer Name' }
    }
});
""")
    
    print("\n2. Checkout Session (Hosted checkout):")
    print("""
// Create checkout session
const checkoutResponse = await fetch('/payments/stripe/checkout-session', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + accessToken
    },
    body: JSON.stringify({
        rental_id: 123,
        success_url: 'https://your-app.com/success',
        cancel_url: 'https://your-app.com/cancel'
    })
});

const { checkout_url } = await checkoutResponse.json();

// Redirect to Stripe checkout
window.location.href = checkout_url;
""")


if __name__ == "__main__":
    print("Stripe Payment Integration Test\n")
    print("=" * 50)
    
    # Test configuration
    test_stripe_configuration()
    
    print("\n" + "=" * 50)
    
    # Print test cards
    print_stripe_test_cards()
    
    print("\n" + "=" * 50)
    
    # Print frontend examples
    print_frontend_examples()
    
    print("\n" + "=" * 50)
    print("\nTo test the full flow:")
    print("1. Configure Stripe in .env file (see STRIPE_SETUP.md)")
    print("2. Start the server: uvicorn app.main:app --reload")
    print("3. Test via API docs: http://localhost:8000/docs")
    print("4. Look for endpoints under 'stripe-payments' tag")
    print("5. Use test card numbers for payment testing")
    print("\nFor automated testing:")
    print('python -c "import asyncio; from test_stripe import test_stripe_integration; asyncio.run(test_stripe_integration())"')
