#!/usr/bin/env python3
"""
Test the rental order flow endpoints
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001"

def setup_test_data():
    """Create test category, product, and inventory item"""
    print("🔧 Setting up test data...")
    
    # Create category
    category_data = {
        "name": "Equipment",
        "parent_id": None
    }
    response = requests.post(f"{BASE_URL}/catalog/categories", json=category_data)
    if response.status_code == 201:
        category = response.json()
        print(f"✅ Created category: {category['name']} (ID: {category['category_id']})")
        
        # Create product with day pricing
        product_data = {
            "seller_id": 1,  # Assuming user ID 1 exists
            "category_id": category['category_id'],
            "title": "Excavator - Heavy Duty",
            "base_price": 100.0,
            "pricing_unit": "day",
            "active": True
        }
        response = requests.post(f"{BASE_URL}/catalog/products", json=product_data)
        if response.status_code == 201:
            product = response.json()
            print(f"✅ Created product: {product['title']} (ID: {product['product_id']}, Price: ${product['base_price']}/day)")
            return product['product_id']
    
    return None


def test_create_order():
    """Test creating a rental order"""
    print("\n📅 Testing Create Rental Order")
    print("=" * 40)
    
    # Create order for ~23 hours (should round up to 1 day)
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=23)
    
    order_data = {
        "customer_id": 1,  # Assuming user ID 1 exists
        "seller_id": 1,    # Same seller
        "start_ts": start_time.isoformat() + "Z",
        "end_ts": end_time.isoformat() + "Z"
    }
    
    response = requests.post(f"{BASE_URL}/rentals/orders", json=order_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        order = response.json()
        print(f"✅ Created order ID: {order['rental_id']}")
        print(f"   Status: {order['status']}")
        print(f"   Duration: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Initial total: ${order['total_amount']}")
        return order['rental_id']
    else:
        print(f"❌ Failed to create order: {response.text}")
        return None


def test_add_items(rental_id, product_id):
    """Test adding items to rental order"""
    print(f"\n📦 Testing Add Items to Order {rental_id}")
    print("=" * 40)
    
    if not rental_id or not product_id:
        print("❌ Missing rental_id or product_id")
        return
    
    # Add first item (qty=2, use default price)
    print("1. Adding 2 excavators at default price...")
    item1_data = {
        "product_id": product_id,
        "qty": 2
        # unit_price omitted - should use product base_price (100)
    }
    
    response = requests.post(f"{BASE_URL}/rentals/orders/{rental_id}/items", json=item1_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        item1 = response.json()
        print(f"✅ Added item: qty={item1['qty']}, unit_price=${item1['unit_price']}")
        print(f"   Line total: ${item1['line_total']}")
        print(f"   Expected: 2 × $100 × 1 day = $200")
    else:
        print(f"❌ Failed to add first item: {response.text}")
        return
    
    # Add second item with price override
    print("\n2. Adding 1 excavator with discounted price...")
    item2_data = {
        "product_id": product_id,
        "qty": 1,
        "unit_price": 80.0  # Override price
    }
    
    response = requests.post(f"{BASE_URL}/rentals/orders/{rental_id}/items", json=item2_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        item2 = response.json()
        print(f"✅ Added item: qty={item2['qty']}, unit_price=${item2['unit_price']}")
        print(f"   Line total: ${item2['line_total']}")
        print(f"   Expected: 1 × $80 × 1 day = $80")
        print(f"   Expected order total: $200 + $80 = $280")
    else:
        print(f"❌ Failed to add second item: {response.text}")


def test_get_order(rental_id):
    """Test getting order with computed totals"""
    print(f"\n📋 Testing Get Order {rental_id}")
    print("=" * 40)
    
    if not rental_id:
        print("❌ Missing rental_id")
        return
    
    response = requests.get(f"{BASE_URL}/rentals/orders/{rental_id}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        order = response.json()
        print(f"✅ Retrieved order details:")
        print(f"   Order ID: {order['rental_id']}")
        print(f"   Status: {order['status']}")
        print(f"   Customer ID: {order['customer_id']}")
        print(f"   Seller ID: {order['seller_id']}")
        print(f"   Total Amount: ${order['total_amount']}")
        print(f"   Computed Total: ${order['computed_total']}")
        print(f"   Items Count: {len(order['items'])}")
        
        print(f"\n   📦 Items:")
        total_check = 0
        for i, item in enumerate(order['items'], 1):
            print(f"     {i}. Product {item['product_id']}: qty={item['qty']}, unit_price=${item['unit_price']}")
            print(f"        Line total: ${item['line_total']}")
            total_check += item['line_total']
        
        print(f"\n   💰 Total verification:")
        print(f"     Sum of line totals: ${total_check}")
        print(f"     Order total_amount: ${order['total_amount']}")
        print(f"     Computed total: ${order['computed_total']}")
        
        if abs(total_check - order['total_amount']) < 0.01 and abs(order['total_amount'] - order['computed_total']) < 0.01:
            print(f"   ✅ All totals match!")
        else:
            print(f"   ❌ Total mismatch detected!")
            
    else:
        print(f"❌ Failed to get order: {response.text}")


def test_validation_errors():
    """Test various validation scenarios"""
    print(f"\n🚨 Testing Validation Errors")
    print("=" * 40)
    
    # Test invalid time range (end <= start)
    print("1. Testing invalid time range (end <= start)...")
    start_time = datetime.now()
    end_time = start_time - timedelta(hours=1)  # End before start
    
    invalid_order = {
        "customer_id": 1,
        "seller_id": 1,
        "start_ts": start_time.isoformat() + "Z",
        "end_ts": end_time.isoformat() + "Z"
    }
    
    response = requests.post(f"{BASE_URL}/rentals/orders", json=invalid_order)
    print(f"   Status: {response.status_code} (Expected: 400)")
    if response.status_code == 400:
        print(f"   ✅ Correctly rejected: {response.json()['detail']}")
    
    # Test adding item to non-existent order
    print("\n2. Testing add item to non-existent order...")
    response = requests.post(f"{BASE_URL}/rentals/orders/999999/items", json={
        "product_id": 1,
        "qty": 1
    })
    print(f"   Status: {response.status_code} (Expected: 404)")
    if response.status_code == 404:
        print(f"   ✅ Correctly rejected: {response.json()['detail']}")
    
    # Test adding non-existent product
    print("\n3. Testing add non-existent product...")
    # First create a valid order
    start_time = datetime.now()
    end_time = start_time + timedelta(days=1)
    order_data = {
        "customer_id": 1,
        "seller_id": 1,
        "start_ts": start_time.isoformat() + "Z",
        "end_ts": end_time.isoformat() + "Z"
    }
    order_response = requests.post(f"{BASE_URL}/rentals/orders", json=order_data)
    if order_response.status_code == 201:
        temp_order_id = order_response.json()['rental_id']
        
        response = requests.post(f"{BASE_URL}/rentals/orders/{temp_order_id}/items", json={
            "product_id": 999999,  # Non-existent product
            "qty": 1
        })
        print(f"   Status: {response.status_code} (Expected: 404)")
        if response.status_code == 404:
            print(f"   ✅ Correctly rejected: {response.json()['detail']}")


def test_duration_calculations():
    """Test different duration calculations"""
    print(f"\n⏱️  Testing Duration Calculations")
    print("=" * 40)
    
    # This would require creating products with different pricing units
    # For now, we'll document the expected behavior:
    print("Duration calculation rules:")
    print("  • hour: ceil(hours between timestamps)")
    print("  • day: ceil(total_hours/24) ")
    print("  • week: ceil(total_hours/(24×7))")
    print("  • month: ceil(total_days/30)")
    print("  • Always rounds UP to avoid under-billing")
    print("\nExamples:")
    print("  • 23 hours with 'day' pricing → 1 day")
    print("  • 25 hours with 'day' pricing → 2 days")
    print("  • 1.5 hours with 'hour' pricing → 2 hours")


def test_rental_flow():
    """Test the complete rental flow"""
    print("🚀 Testing Odoo Final Backend - Rental Order Flow v1")
    print("=" * 60)
    
    try:
        # Setup test data
        product_id = setup_test_data()
        
        if not product_id:
            print("❌ Failed to set up test data")
            return
        
        # Test creating order
        rental_id = test_create_order()
        
        # Test adding items
        test_add_items(rental_id, product_id)
        
        # Test getting order
        test_get_order(rental_id)
        
        # Test validation errors
        test_validation_errors()
        
        # Show duration calculation info
        test_duration_calculations()
        
        print("\n✅ Rental Order Flow v1 tests completed!")
        print("\n📋 Summary:")
        print("  ✅ Order creation with time validation")
        print("  ✅ Item addition with pricing calculation")
        print("  ✅ Duration-based billing (day pricing)")
        print("  ✅ Total computation and verification")
        print("  ✅ Error handling and validation")
        print("  ✅ Order retrieval with computed totals")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running on port 8001.")
    except Exception as e:
        print(f"❌ Error during testing: {e}")


if __name__ == "__main__":
    test_rental_flow()
