"""
Optimized service layer with caching and performance improvements.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from functools import lru_cache
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.user import User, UserRole, Role
from ..models.rentals import RentalOrder, RentalItem
from ..models.catalog import Product, Category
from ..models.inventory import InventoryItem
from ..utils.query_optimizer import QueryOptimizer, RentalQueryOptimizer
from ..middleware.performance import cache

class OptimizedUserService:
    """Optimized user service with caching and query optimization."""
    
    def __init__(self, db: Session):
        self.db = db
        self.query_optimizer = QueryOptimizer(db, User)
    
    @lru_cache(maxsize=128)
    def get_user_by_email_cached(self, email: str) -> Optional[User]:
        """Get user by email with caching."""
        cache_key = f"user:email:{email}"
        cached_user = cache.get(cache_key)
        
        if cached_user:
            return cached_user
        
        user = self.db.query(User).filter(User.email == email).first()
        if user:
            cache.set(cache_key, user, ttl=300)  # Cache for 5 minutes
        
        return user
    
    def get_user_with_roles(self, user_id: int) -> Optional[User]:
        """Get user with roles using optimized query."""
        return self.query_optimizer.get_with_relations(user_id, 'user_roles')
    
    def get_users_paginated(self, page: int = 1, per_page: int = 20, **filters) -> Dict[str, Any]:
        """Get paginated users with optimized queries."""
        return self.query_optimizer.get_paginated(page, per_page, **filters)
    
    def bulk_update_users(self, updates: List[Dict[str, Any]]) -> int:
        """Bulk update users efficiently."""
        return self.query_optimizer.bulk_update(updates, 'user_id')

class OptimizedRentalService:
    """Optimized rental service with advanced query optimization."""
    
    def __init__(self, db: Session):
        self.db = db
        self.rental_optimizer = RentalQueryOptimizer(db)
    
    def get_user_rentals_optimized(self, user_id: int, status: Optional[str] = None) -> List[RentalOrder]:
        """Get user rentals with all related data in optimized queries."""
        return self.rental_optimizer.get_user_rentals_with_details(user_id, status)
    
    def get_rental_analytics(self, start_date=None, end_date=None) -> Dict[str, Any]:
        """Get comprehensive rental analytics."""
        cache_key = f"analytics:{start_date}:{end_date}"
        cached_analytics = cache.get(cache_key)
        
        if cached_analytics:
            return cached_analytics
        
        # Revenue summary
        revenue_summary = self.rental_optimizer.get_revenue_summary(start_date, end_date)
        
        # Popular products
        popular_products = self.rental_optimizer.get_popular_products(10)
        
        # Status distribution
        status_distribution = self.db.query(
            RentalOrder.status,
            func.count(RentalOrder.rental_order_id).label('count')
        ).group_by(RentalOrder.status).all()
        
        analytics = {
            "revenue_summary": {
                "total_revenue": float(revenue_summary.total_revenue or 0),
                "total_orders": revenue_summary.total_orders or 0,
                "avg_order_value": float(revenue_summary.avg_order_value or 0)
            },
            "popular_products": [
                {
                    "product_id": product.Product.product_id,
                    "name": product.Product.name,
                    "rental_count": product.rental_count
                }
                for product in popular_products
            ],
            "status_distribution": [
                {"status": status, "count": count}
                for status, count in status_distribution
            ]
        }
        
        # Cache for 10 minutes
        cache.set(cache_key, analytics, ttl=600)
        return analytics
    
    def create_rental_optimized(self, rental_data: Dict[str, Any]) -> RentalOrder:
        """Create rental with optimized inventory updates."""
        # Create rental order
        rental = RentalOrder(**rental_data)
        self.db.add(rental)
        self.db.flush()  # Get ID without committing
        
        # Clear related caches
        cache.delete(f"user:rentals:{rental.customer_id}")
        
        return rental

class OptimizedInventoryService:
    """Optimized inventory service with availability caching."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_product_availability(self, product_id: int) -> Dict[str, Any]:
        """Get product availability with caching."""
        cache_key = f"inventory:product:{product_id}"
        cached_availability = cache.get(cache_key)
        
        if cached_availability:
            return cached_availability
        
        inventory_item = self.db.query(InventoryItem).filter(
            InventoryItem.product_id == product_id
        ).first()
        
        if inventory_item:
            availability = {
                "product_id": product_id,
                "available_quantity": inventory_item.available_quantity,
                "reserved_quantity": inventory_item.reserved_quantity,
                "total_quantity": inventory_item.total_quantity,
                "is_available": inventory_item.available_quantity > 0
            }
            
            # Cache for 2 minutes (inventory changes frequently)
            cache.set(cache_key, availability, ttl=120)
            return availability
        
        return {
            "product_id": product_id,
            "available_quantity": 0,
            "is_available": False
        }
    
    def bulk_update_inventory(self, updates: List[Dict[str, Any]]) -> None:
        """Bulk update inventory and clear related caches."""
        for update in updates:
            product_id = update.get('product_id')
            if product_id:
                # Clear cache
                cache.delete(f"inventory:product:{product_id}")
        
        # Perform bulk update
        for update in updates:
            product_id = update.pop('product_id')
            self.db.query(InventoryItem).filter(
                InventoryItem.product_id == product_id
            ).update(update)

class OptimizedCatalogService:
    """Optimized catalog service with product caching."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_products_with_availability(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get products with availability information."""
        cache_key = f"products:category:{category_id}"
        cached_products = cache.get(cache_key)
        
        if cached_products:
            return cached_products
        
        query = self.db.query(Product, InventoryItem).join(
            InventoryItem, Product.product_id == InventoryItem.product_id, isouter=True
        )
        
        if category_id:
            query = query.filter(Product.category_id == category_id)
        
        results = query.all()
        
        products = []
        for product, inventory in results:
            product_data = {
                "product_id": product.product_id,
                "name": product.name,
                "description": product.description,
                "base_price": float(product.base_price),
                "category_id": product.category_id,
                "available_quantity": inventory.available_quantity if inventory else 0,
                "is_available": inventory.available_quantity > 0 if inventory else False
            }
            products.append(product_data)
        
        # Cache for 5 minutes
        cache.set(cache_key, products, ttl=300)
        return products
    
    @lru_cache(maxsize=64)
    def get_categories_cached(self) -> List[Category]:
        """Get categories with caching."""
        cache_key = "categories:all"
        cached_categories = cache.get(cache_key)
        
        if cached_categories:
            return cached_categories
        
        categories = self.db.query(Category).all()
        cache.set(cache_key, categories, ttl=600)  # Cache for 10 minutes
        return categories

class ServiceFactory:
    """Factory for creating optimized service instances."""
    
    @staticmethod
    def create_user_service(db: Session) -> OptimizedUserService:
        return OptimizedUserService(db)
    
    @staticmethod
    def create_rental_service(db: Session) -> OptimizedRentalService:
        return OptimizedRentalService(db)
    
    @staticmethod
    def create_inventory_service(db: Session) -> OptimizedInventoryService:
        return OptimizedInventoryService(db)
    
    @staticmethod
    def create_catalog_service(db: Session) -> OptimizedCatalogService:
        return OptimizedCatalogService(db)

# Utility functions for easy access
def get_optimized_user_service(db: Session) -> OptimizedUserService:
    return ServiceFactory.create_user_service(db)

def get_optimized_rental_service(db: Session) -> OptimizedRentalService:
    return ServiceFactory.create_rental_service(db)

def get_optimized_inventory_service(db: Session) -> OptimizedInventoryService:
    return ServiceFactory.create_inventory_service(db)

def get_optimized_catalog_service(db: Session) -> OptimizedCatalogService:
    return ServiceFactory.create_catalog_service(db)
