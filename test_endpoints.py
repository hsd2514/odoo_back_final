#!/usr/bin/env python3
"""
Test the authentication endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8001"

def test_registration():
    """Test user registration"""
    print("=== Testing User Registration ===")
    
    registration_data = {
        "email": "test@example.com",
        "full_name": "Test User",
        "phone": "1234567890",
        "password": "testpass123",
        "confirm_password": "testpass123"
    }
    
    response = requests.post(f"{BASE_URL}/users/register", json=registration_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
    
    if response.status_code in [200, 201] and response.text:
        try:
            return response.json()
        except:
            print("Failed to parse JSON response")
            return None
    return None

def test_login():
    """Test user login"""
    print("\n=== Testing User Login ===")
    
    login_data = {
        "email": "test@example.com",
        "password": "testpass123"
    }
    
    response = requests.post(f"{BASE_URL}/users/login", json=login_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        return response.json()
    return None

if __name__ == "__main__":
    print("🚀 Testing Odoo Final Backend Authentication")
    print("=" * 50)
    
    # Test registration
    registration_result = test_registration()
    
    # Test login
    login_result = test_login()
    
    if registration_result and login_result:
        print("\n✅ All tests passed!")
        print(f"Access Token: {login_result.get('access_token', 'N/A')[:50]}...")
    else:
        print("\n❌ Some tests failed!")
