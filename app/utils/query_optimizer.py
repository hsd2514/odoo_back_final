"""
Query optimization utilities for improving database performance.
"""

from __future__ import annotations

from typing import Optional, List, Type, TypeVar, Generic
from sqlalchemy import func, text
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy.orm.strategy_options import Load

from ..database_optimized import Base

T = TypeVar('T', bound=Base)

class QueryOptimizer(Generic[T]):
    """Utility class for optimizing database queries."""
    
    def __init__(self, session: Session, model: Type[T]):
        self.session = session
        self.model = model
    
    def get_with_relations(self, id: int, *relations) -> Optional[T]:
        """Get entity by ID with eager loading of specified relations."""
        query = self.session.query(self.model)
        
        # Add eager loading for each relation
        for relation in relations:
            query = query.options(selectinload(getattr(self.model, relation)))
        
        return query.filter(self.model.id == id).first()
    
    def get_paginated(self, page: int = 1, per_page: int = 20, **filters) -> dict:
        """Get paginated results with optional filters."""
        query = self.session.query(self.model)
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)
        
        # Count total before pagination
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }
    
    def bulk_create(self, objects: List[dict]) -> List[T]:
        """Efficiently create multiple objects."""
        instances = [self.model(**obj) for obj in objects]
        self.session.add_all(instances)
        self.session.flush()  # Get IDs without committing
        return instances
    
    def bulk_update(self, updates: List[dict], id_key: str = 'id') -> int:
        """Efficiently update multiple objects."""
        if not updates:
            return 0
        
        # Use bulk update for better performance
        updated_count = 0
        for update_data in updates:
            id_value = update_data.pop(id_key)
            result = self.session.query(self.model).filter(
                getattr(self.model, id_key) == id_value
            ).update(update_data)
            updated_count += result
        
        return updated_count

class RentalQueryOptimizer:
    """Specialized query optimizer for rental-related operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_user_rentals_with_details(self, user_id: int, status: Optional[str] = None):
        """Get user rentals with all related data in a single query."""
        from ..models.rentals import RentalOrder, RentalItem
        from ..models.catalog import Product
        from ..models.user import User
        
        query = self.session.query(RentalOrder).options(
            joinedload(RentalOrder.customer),
            joinedload(RentalOrder.seller),
            selectinload(RentalOrder.rental_items).selectinload(RentalItem.product)
        ).filter(RentalOrder.customer_id == user_id)
        
        if status:
            query = query.filter(RentalOrder.status == status)
        
        return query.all()
    
    def get_popular_products(self, limit: int = 10):
        """Get most popular products based on rental frequency."""
        from ..models.rentals import RentalItem
        from ..models.catalog import Product
        
        return self.session.query(
            Product,
            func.count(RentalItem.rental_item_id).label('rental_count')
        ).join(
            RentalItem, Product.product_id == RentalItem.product_id
        ).group_by(
            Product.product_id
        ).order_by(
            func.count(RentalItem.rental_item_id).desc()
        ).limit(limit).all()
    
    def get_revenue_summary(self, start_date=None, end_date=None):
        """Get revenue summary with optimized aggregation."""
        from ..models.rentals import RentalOrder
        
        query = self.session.query(
            func.sum(RentalOrder.total_amount).label('total_revenue'),
            func.count(RentalOrder.rental_order_id).label('total_orders'),
            func.avg(RentalOrder.total_amount).label('avg_order_value')
        )
        
        if start_date:
            query = query.filter(RentalOrder.start_ts >= start_date)
        if end_date:
            query = query.filter(RentalOrder.end_ts <= end_date)
        
        return query.first()

class DatabaseIndexOptimizer:
    """Utility for managing database indexes for performance."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_performance_indexes(self):
        """Create indexes for common query patterns."""
        indexes = [
            # User indexes
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id)",
            
            # Rental indexes
            "CREATE INDEX IF NOT EXISTS idx_rental_orders_customer_id ON rental_orders(customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_rental_orders_seller_id ON rental_orders(seller_id)",
            "CREATE INDEX IF NOT EXISTS idx_rental_orders_status ON rental_orders(status)",
            "CREATE INDEX IF NOT EXISTS idx_rental_orders_dates ON rental_orders(start_ts, end_ts)",
            
            # Product indexes
            "CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id)",
            "CREATE INDEX IF NOT EXISTS idx_products_seller_id ON products(seller_id)",
            "CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)",
            
            # Inventory indexes
            "CREATE INDEX IF NOT EXISTS idx_inventory_product_id ON inventory_items(product_id)",
            "CREATE INDEX IF NOT EXISTS idx_inventory_available ON inventory_items(available_quantity)",
            
            # Billing indexes
            "CREATE INDEX IF NOT EXISTS idx_invoices_rental_order_id ON invoices(rental_order_id)",
            "CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments(invoice_id)",
        ]
        
        for index_sql in indexes:
            try:
                self.session.execute(text(index_sql))
                print(f"✅ Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
            except Exception as e:
                print(f"⚠️  Index creation skipped: {e}")
        
        self.session.commit()
    
    def analyze_slow_queries(self):
        """Analyze and suggest optimizations for slow queries."""
        # This would contain database-specific query analysis
        # For PostgreSQL, you might use pg_stat_statements
        # For SQLite, you might use EXPLAIN QUERY PLAN
        print("📊 Query analysis feature - implement based on your database type")

def create_query_optimizer(session: Session, model: Type[T]) -> QueryOptimizer[T]:
    """Factory function to create a query optimizer for a specific model."""
    return QueryOptimizer(session, model)

def optimize_database_schema(session: Session):
    """Apply all database optimizations."""
    print("🔧 Optimizing database schema...")
    
    index_optimizer = DatabaseIndexOptimizer(session)
    index_optimizer.create_performance_indexes()
    
    print("✅ Database optimization complete!")
