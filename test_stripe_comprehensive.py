#!/usr/bin/env python3
"""
Comprehensive Stripe integration verification test
"""

def test_imports():
    """Test all Stripe-related imports"""
    print("=== Testing Imports ===")
    
    try:
        # Test core service import
        from app.services.stripe_service import stripe_service
        print("✅ Stripe service import")
        
        # Test router import
        from app.routers.stripe_payments import router
        print("✅ Stripe router import")
        
        # Test schemas import
        from app.schemas.payments import (
            StripePaymentIntentCreate, StripeCheckoutSessionCreate,
            StripePaymentIntentResponse, StripePaymentStatusResponse
        )
        print("✅ Stripe schemas import")
        
        # Test main app import
        from app.main import app
        print("✅ Main app import")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_configuration():
    """Test Stripe configuration"""
    print("\n=== Testing Configuration ===")
    
    try:
        from app.config import get_settings
        settings = get_settings()
        
        print(f"✅ Currency: {settings.stripe_currency}")
        print(f"✅ Success URL: {settings.payment_success_url}")
        print(f"✅ Cancel URL: {settings.payment_cancel_url}")
        
        # Check if keys are configured
        if settings.stripe_secret_key:
            print("✅ Secret key configured")
        else:
            print("⚠️  Secret key not configured")
        
        if settings.stripe_publishable_key:
            print("✅ Publishable key configured")
        else:
            print("⚠️  Publishable key not configured")
        
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_service_functionality():
    """Test Stripe service functionality"""
    print("\n=== Testing Service Functionality ===")
    
    try:
        from app.services.stripe_service import stripe_service
        
        # Test amount conversion
        test_amounts = [0.50, 10.99, 100.00, 999.99]
        for amount in test_amounts:
            cents = stripe_service.dollars_to_cents(amount)
            dollars = stripe_service.cents_to_dollars(cents)
            if dollars == amount:
                print(f"✅ Amount conversion: ${amount} ↔ {cents} cents")
            else:
                print(f"❌ Amount conversion failed: ${amount} ≠ ${dollars}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Service functionality test failed: {e}")
        return False


def test_api_routes():
    """Test API routes are registered"""
    print("\n=== Testing API Routes ===")
    
    try:
        from app.main import app
        
        # Get all routes
        stripe_routes = []
        for route in app.routes:
            if hasattr(route, 'path') and '/payments/stripe' in route.path:
                stripe_routes.append({
                    'path': route.path,
                    'methods': list(route.methods) if hasattr(route, 'methods') else []
                })
        
        expected_routes = [
            '/payments/stripe/config',
            '/payments/stripe/payment-intent',
            '/payments/stripe/checkout-session',
            '/payments/stripe/confirm-payment',
            '/payments/stripe/payment-status/{payment_intent_id}',
            '/payments/stripe/refund',
            '/payments/stripe/customer',
            '/payments/stripe/rental/{rental_id}/summary',
            '/payments/stripe/webhook'
        ]
        
        found_paths = [route['path'] for route in stripe_routes]
        
        for expected in expected_routes:
            if expected in found_paths:
                print(f"✅ Route registered: {expected}")
            else:
                print(f"❌ Route missing: {expected}")
                return False
        
        print(f"✅ All {len(expected_routes)} Stripe routes registered")
        return True
        
    except Exception as e:
        print(f"❌ API routes test failed: {e}")
        return False


def test_api_endpoints():
    """Test API endpoints with test client"""
    print("\n=== Testing API Endpoints ===")
    
    try:
        from app.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test OpenAPI docs
        response = client.get("/docs")
        if response.status_code == 200:
            print("✅ OpenAPI documentation accessible")
        else:
            print(f"❌ OpenAPI docs failed: {response.status_code}")
            return False
        
        # Test Stripe config endpoint
        response = client.get("/payments/stripe/config")
        if response.status_code in [200, 503]:  # 503 if not configured
            print(f"✅ Stripe config endpoint responding ({response.status_code})")
        else:
            print(f"❌ Stripe config endpoint failed: {response.status_code}")
            return False
        
        # Test authenticated endpoints (should fail without auth)
        auth_endpoints = [
            "/payments/stripe/payment-intent",
            "/payments/stripe/checkout-session",
            "/payments/stripe/customer"
        ]
        
        for endpoint in auth_endpoints:
            response = client.post(endpoint, json={"rental_id": 1})
            if response.status_code == 401:  # Unauthorized
                print(f"✅ Auth required for: {endpoint}")
            else:
                print(f"⚠️  Unexpected response for {endpoint}: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        return False


def test_schema_validation():
    """Test Pydantic schema validation"""
    print("\n=== Testing Schema Validation ===")
    
    try:
        from app.schemas.payments import (
            StripePaymentIntentCreate, StripeCheckoutSessionCreate,
            StripePaymentIntentResponse
        )
        
        # Test valid data
        valid_payment_intent = {
            "rental_id": 123,
            "save_payment_method": False
        }
        
        schema = StripePaymentIntentCreate(**valid_payment_intent)
        print(f"✅ Payment Intent schema validation: rental_id={schema.rental_id}")
        
        valid_checkout = {
            "rental_id": 456,
            "collect_shipping_address": False
        }
        
        schema = StripeCheckoutSessionCreate(**valid_checkout)
        print(f"✅ Checkout Session schema validation: rental_id={schema.rental_id}")
        
        # Test required fields
        try:
            StripePaymentIntentCreate(save_payment_method=True)  # Missing rental_id
            print("❌ Schema validation too lenient")
            return False
        except Exception:
            print("✅ Schema validation enforces required fields")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema validation test failed: {e}")
        return False


def run_comprehensive_test():
    """Run all tests and provide summary"""
    print("🧪 Comprehensive Stripe Integration Test")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Service Functionality", test_service_functionality),
        ("API Routes", test_api_routes),
        ("API Endpoints", test_api_endpoints),
        ("Schema Validation", test_schema_validation)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Stripe integration is ready!")
        print("\nNext steps:")
        print("1. Configure Stripe keys in .env file")
        print("2. Start server: uvicorn app.main:app --reload")
        print("3. Test at: http://localhost:8000/docs")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    run_comprehensive_test()
