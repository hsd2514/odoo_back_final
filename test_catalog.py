#!/usr/bin/env python3
"""
Test the catalog CRUD endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8001"

def test_categories():
    """Test category CRUD operations"""
    print("🗂️  Testing Category CRUD")
    print("=" * 40)
    
    # Create a root category
    print("\n1. Creating root category...")
    root_category_data = {
        "name": "Electronics",
        "parent_id": None
    }
    
    response = requests.post(f"{BASE_URL}/catalog/categories", json=root_category_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        root_category = response.json()
        print(f"Created: {root_category['name']} (ID: {root_category['category_id']})")
        
        # Create a subcategory
        print("\n2. Creating subcategory...")
        sub_category_data = {
            "name": "Laptops",
            "parent_id": root_category['category_id']
        }
        
        response = requests.post(f"{BASE_URL}/catalog/categories", json=sub_category_data)
        print(f"Status: {response.status_code}")
        if response.status_code == 201:
            sub_category = response.json()
            print(f"Created: {sub_category['name']} (ID: {sub_category['category_id']})")
            
            # Get all categories
            print("\n3. Getting all categories...")
            response = requests.get(f"{BASE_URL}/catalog/categories")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                categories = response.json()
                print(f"Total categories: {categories['total']}")
                for cat in categories['categories']:
                    print(f"  - {cat['name']} (ID: {cat['category_id']}, Parent: {cat['parent_id']})")
                
                return root_category['category_id'], sub_category['category_id']
    
    return None, None


def test_products(category_id):
    """Test product CRUD operations"""
    print("\n💻 Testing Product CRUD")
    print("=" * 40)
    
    if not category_id:
        print("❌ No category available for product testing")
        return None
    
    # Create a product with assets
    print("\n1. Creating product with assets...")
    product_data = {
        "seller_id": 1,  # Assuming user ID 1 exists
        "category_id": category_id,
        "title": "MacBook Pro 16 inch",
        "base_price": 2499.99,
        "pricing_unit": "piece",
        "active": True,
        "assets": [
            {
                "asset_type": "image",
                "uri": "https://example.com/macbook-front.jpg",
                "drm_protected": False
            },
            {
                "asset_type": "image", 
                "uri": "https://example.com/macbook-side.jpg",
                "drm_protected": False
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/catalog/products", json=product_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        product = response.json()
        print(f"Created: {product['title']} (ID: {product['product_id']})")
        print(f"Assets: {len(product['assets'])} assets created")
        
        # Get product by ID
        print("\n2. Getting product by ID...")
        response = requests.get(f"{BASE_URL}/catalog/products/{product['product_id']}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            fetched_product = response.json()
            print(f"Retrieved: {fetched_product['title']}")
            print(f"Price: ${fetched_product['base_price']} per {fetched_product['pricing_unit']}")
            
            # Update product
            print("\n3. Updating product...")
            update_data = {
                "base_price": 2299.99,
                "title": "MacBook Pro 16 inch (Refurbished)"
            }
            
            response = requests.put(f"{BASE_URL}/catalog/products/{product['product_id']}", json=update_data)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                updated_product = response.json()
                print(f"Updated: {updated_product['title']}")
                print(f"New Price: ${updated_product['base_price']}")
                
                return product['product_id']
    
    return None


def test_product_assets(product_id):
    """Test product asset operations"""
    print("\n🖼️  Testing Product Assets")
    print("=" * 40)
    
    if not product_id:
        print("❌ No product available for asset testing")
        return
    
    # Get existing assets
    print("\n1. Getting existing product assets...")
    response = requests.get(f"{BASE_URL}/catalog/products/{product_id}/assets")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        assets = response.json()
        print(f"Existing assets: {assets['total']}")
        for asset in assets['assets']:
            print(f"  - {asset['asset_type']}: {asset['uri']} (ID: {asset['asset_id']})")
    
    # Add new asset
    print("\n2. Adding new asset...")
    new_asset_data = {
        "asset_type": "video",
        "uri": "https://example.com/macbook-demo.mp4",
        "drm_protected": True
    }
    
    response = requests.post(f"{BASE_URL}/catalog/products/{product_id}/assets", json=new_asset_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        new_asset = response.json()
        print(f"Created: {new_asset['asset_type']} asset (ID: {new_asset['asset_id']})")
        
        # Update asset
        print("\n3. Updating asset...")
        update_asset_data = {
            "drm_protected": False
        }
        
        response = requests.put(f"{BASE_URL}/catalog/assets/{new_asset['asset_id']}", json=update_asset_data)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            updated_asset = response.json()
            print(f"Updated: DRM protected = {updated_asset['drm_protected']}")


def test_catalog_endpoints():
    """Test all catalog endpoints"""
    print("🚀 Testing Odoo Final Backend - Catalog CRUD")
    print("=" * 50)
    
    try:
        # Test categories
        root_category_id, sub_category_id = test_categories()
        
        # Test products
        product_id = test_products(sub_category_id or root_category_id)
        
        # Test product assets
        test_product_assets(product_id)
        
        print("\n✅ Catalog CRUD tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the server is running on port 8001.")
    except Exception as e:
        print(f"❌ Error during testing: {e}")


if __name__ == "__main__":
    test_catalog_endpoints()
