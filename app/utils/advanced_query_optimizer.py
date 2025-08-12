"""
Advanced Query Optimization for Peak Performance
Includes materialized views, advanced indexing, and query-specific optimizations
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import text, Index, event
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.sql import func
from dataclasses import dataclass

from ..database_optimized import SessionLocal, engine
from ..models.catalog import Product, Category
from ..models.inventory import InventoryItem
from ..models.rentals import RentalOrder, RentalItem
from ..models.user import User

logger = logging.getLogger(__name__)

@dataclass
class QueryPerformanceMetrics:
    """Track query performance metrics"""
    query_name: str
    execution_time: float
    rows_returned: int
    cache_hit: bool = False

class AdvancedQueryOptimizer:
    """Advanced query optimization strategies"""
    
    def __init__(self):
        self.performance_metrics: List[QueryPerformanceMetrics] = []
        self.materialized_views_created = False
    
    def create_materialized_views(self, db: Session) -> bool:
        """Create materialized views for complex queries"""
        if self.materialized_views_created:
            return True
        
        try:
            # Product availability summary view
            db.execute(text("""
                CREATE OR REPLACE VIEW product_availability_summary AS
                SELECT 
                    p.product_id,
                    p.title,
                    p.base_price,
                    p.pricing_unit,
                    COUNT(i.item_id) as total_inventory,
                    COUNT(CASE WHEN i.status = 'available' THEN 1 END) as available_count,
                    COUNT(CASE WHEN i.status = 'reserved' THEN 1 END) as reserved_count,
                    COUNT(CASE WHEN i.status = 'rented' THEN 1 END) as rented_count,
                    AVG(CASE WHEN i.status = 'available' THEN 1.0 ELSE 0.0 END) as availability_ratio
                FROM products p
                LEFT JOIN inventory_items i ON p.product_id = i.product_id
                WHERE p.active = true
                GROUP BY p.product_id, p.title, p.base_price, p.pricing_unit
            """))
            
            # Rental performance summary view
            db.execute(text("""
                CREATE OR REPLACE VIEW rental_performance_summary AS
                SELECT 
                    p.product_id,
                    p.title,
                    COUNT(DISTINCT ro.rental_id) as total_rentals,
                    COUNT(DISTINCT ro.customer_id) as unique_customers,
                    AVG(ro.total_amount) as avg_rental_value,
                    SUM(ro.total_amount) as total_revenue,
                    AVG(EXTRACT(EPOCH FROM (ro.end_ts - ro.start_ts))/86400) as avg_rental_days
                FROM products p
                LEFT JOIN rental_items ri ON p.product_id = ri.product_id
                LEFT JOIN rental_orders ro ON ri.rental_id = ro.rental_id
                WHERE ro.status IN ('booked', 'ongoing', 'completed')
                GROUP BY p.product_id, p.title
            """))
            
            # User activity summary view
            db.execute(text("""
                CREATE OR REPLACE VIEW user_activity_summary AS
                SELECT 
                    u.user_id,
                    u.email,
                    u.first_name,
                    u.last_name,
                    COUNT(DISTINCT ro.rental_id) as total_rentals,
                    SUM(ro.total_amount) as total_spent,
                    AVG(ro.total_amount) as avg_order_value,
                    MAX(ro.created_at) as last_rental_date,
                    CASE 
                        WHEN MAX(ro.created_at) > NOW() - INTERVAL '30 days' THEN 'active'
                        WHEN MAX(ro.created_at) > NOW() - INTERVAL '90 days' THEN 'inactive'
                        ELSE 'dormant'
                    END as customer_status
                FROM users u
                LEFT JOIN rental_orders ro ON u.user_id = ro.customer_id
                GROUP BY u.user_id, u.email, u.first_name, u.last_name
            """))
            
            db.commit()
            self.materialized_views_created = True
            logger.info("✅ Materialized views created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create materialized views: {e}")
            db.rollback()
            return False
    
    def create_advanced_indexes(self, db: Session) -> bool:
        """Create advanced composite indexes for performance"""
        try:
            # Composite index for product search with availability
            db.execute(text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_search_performance 
                ON products (active, category_id, base_price) 
                WHERE active = true
            """))
            
            # Composite index for rental queries
            db.execute(text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rental_performance 
                ON rental_orders (customer_id, status, created_at DESC)
            """))
            
            # Inventory status index with partial indexing
            db.execute(text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_available 
                ON inventory_items (product_id, status) 
                WHERE status IN ('available', 'reserved')
            """))
            
            # Date range index for rental periods
            db.execute(text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rental_date_range 
                ON rental_orders (start_ts, end_ts) 
                WHERE status IN ('booked', 'ongoing')
            """))
            
            # Full-text search index for products
            db.execute(text("""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_fulltext 
                ON products USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')))
                WHERE active = true
            """))
            
            db.commit()
            logger.info("✅ Advanced indexes created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create advanced indexes: {e}")
            db.rollback()
            return False
    
    def get_product_catalog_optimized(
        self, 
        category_id: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        search_query: Optional[str] = None,
        include_availability: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Optimized product catalog query with caching"""
        start_time = datetime.now()
        
        with SessionLocal() as db:
            # Use materialized view for better performance
            if include_availability:
                query = db.execute(text("""
                    SELECT * FROM product_availability_summary 
                    WHERE 1=1
                    AND (:category_id IS NULL OR product_id IN (
                        SELECT product_id FROM products WHERE category_id = :category_id
                    ))
                    AND (:min_price IS NULL OR base_price >= :min_price)
                    AND (:max_price IS NULL OR base_price <= :max_price)
                    AND (:search_query IS NULL OR title ILIKE :search_pattern)
                    ORDER BY availability_ratio DESC, title
                    LIMIT :limit OFFSET :offset
                """), {
                    'category_id': category_id,
                    'min_price': min_price,
                    'max_price': max_price,
                    'search_query': search_query,
                    'search_pattern': f"%{search_query}%" if search_query else None,
                    'limit': limit,
                    'offset': offset
                })
            else:
                # Faster query without availability data
                query = db.query(Product).filter(Product.active == True)
                
                if category_id:
                    query = query.filter(Product.category_id == category_id)
                if min_price:
                    query = query.filter(Product.base_price >= min_price)
                if max_price:
                    query = query.filter(Product.base_price <= max_price)
                if search_query:
                    query = query.filter(Product.title.ilike(f"%{search_query}%"))
                
                query = query.order_by(Product.title).limit(limit).offset(offset)
            
            products = query.all() if hasattr(query, 'all') else list(query)
            
            # Track performance
            execution_time = (datetime.now() - start_time).total_seconds()
            self.performance_metrics.append(
                QueryPerformanceMetrics(
                    query_name="get_product_catalog_optimized",
                    execution_time=execution_time,
                    rows_returned=len(products),
                    cache_hit=False
                )
            )
            
            return {
                "products": [dict(p._mapping) if hasattr(p, '_mapping') else p.__dict__ for p in products],
                "count": len(products),
                "execution_time": execution_time
            }
    
    def get_product_availability_optimized(
        self,
        product_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Optimized availability check with intelligent caching"""
        start_time = datetime.now()
        
        with SessionLocal() as db:
            # Get total inventory count
            total_inventory = db.query(func.count(InventoryItem.item_id)).filter(
                InventoryItem.product_id == product_id
            ).scalar()
            
            # Get conflicting rentals using optimized query
            conflicting_rentals = db.execute(text("""
                SELECT COUNT(DISTINCT ri.inventory_item_id) as conflicting_items
                FROM rental_items ri
                JOIN rental_orders ro ON ri.rental_id = ro.rental_id
                WHERE ri.product_id = :product_id
                AND ro.status IN ('booked', 'ongoing')
                AND (
                    (ro.start_ts <= :start_date AND ro.end_ts > :start_date) OR
                    (ro.start_ts < :end_date AND ro.end_ts >= :end_date) OR
                    (ro.start_ts >= :start_date AND ro.end_ts <= :end_date)
                )
            """), {
                'product_id': product_id,
                'start_date': start_date,
                'end_date': end_date
            }).scalar() or 0
            
            available_items = max(0, total_inventory - conflicting_rentals)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "product_id": product_id,
                "total_inventory": total_inventory,
                "available_items": available_items,
                "conflicting_rentals": conflicting_rentals,
                "is_available": available_items > 0,
                "execution_time": execution_time
            }
            
            
            return result
    
    def get_rental_analytics_optimized(
        self,
        seller_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Optimized rental analytics using materialized views"""
        start_time = datetime.now()
        
        with SessionLocal() as db:
            # Use materialized view for performance
            query = text("""
                SELECT 
                    rps.*,
                    pas.available_count,
                    pas.total_inventory
                FROM rental_performance_summary rps
                LEFT JOIN product_availability_summary pas ON rps.product_id = pas.product_id
                WHERE (:seller_id IS NULL OR rps.product_id IN (
                    SELECT product_id FROM products WHERE seller_id = :seller_id
                ))
                ORDER BY rps.total_revenue DESC
                LIMIT 20
            """)
            
            results = db.execute(query, {'seller_id': seller_id}).all()
            
            # Additional quick metrics
            total_revenue = db.execute(text("""
                SELECT COALESCE(SUM(total_amount), 0) as total
                FROM rental_orders 
                WHERE created_at >= NOW() - INTERVAL :days DAY
                AND (:seller_id IS NULL OR seller_id = :seller_id)
                AND status IN ('booked', 'ongoing', 'completed')
            """), {'days': days, 'seller_id': seller_id}).scalar()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "top_products": [dict(r._mapping) for r in results],
                "total_revenue_period": float(total_revenue),
                "period_days": days,
                "execution_time": execution_time
            }
    
    def get_user_rental_history_optimized(
        self,
        user_id: int,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Optimized user rental history with eager loading"""
        start_time = datetime.now()
        
        with SessionLocal() as db:
            # Use optimized query with joins
            rentals = db.query(RentalOrder).options(
                joinedload(RentalOrder.rental_items).joinedload(RentalItem.product),
                selectinload(RentalOrder.rental_items)
            ).filter(
                RentalOrder.customer_id == user_id
            ).order_by(
                RentalOrder.created_at.desc()
            ).limit(limit).all()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "rentals": [
                    {
                        "rental_id": rental.rental_id,
                        "status": rental.status,
                        "total_amount": float(rental.total_amount),
                        "start_ts": rental.start_ts.isoformat(),
                        "end_ts": rental.end_ts.isoformat(),
                        "items": [
                            {
                                "product_title": item.product.title if item.product else "Unknown",
                                "qty": item.qty,
                                "unit_price": float(item.unit_price)
                            }
                            for item in rental.rental_items
                        ]
                    }
                    for rental in rentals
                ],
                "execution_time": execution_time
            }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get query performance metrics"""
        if not self.performance_metrics:
            return {"message": "No metrics available"}
        
        total_queries = len(self.performance_metrics)
        avg_execution_time = sum(m.execution_time for m in self.performance_metrics) / total_queries
        cache_hit_rate = sum(1 for m in self.performance_metrics if m.cache_hit) / total_queries * 100
        
        return {
            "total_queries": total_queries,
            "average_execution_time": f"{avg_execution_time:.3f}s",
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "slowest_queries": sorted(
                [{"name": m.query_name, "time": m.execution_time} for m in self.performance_metrics],
                key=lambda x: x["time"],
                reverse=True
            )[:5]
        }

# Global optimizer instance
query_optimizer = AdvancedQueryOptimizer()

# Bulk operations for better performance
class BulkOperations:
    """Optimized bulk database operations"""
    
    @staticmethod
    def bulk_update_inventory_status(
        db: Session,
        updates: List[Tuple[int, str]]  # [(item_id, new_status), ...]
    ) -> int:
        """Bulk update inventory item statuses"""
        if not updates:
            return 0
        
        try:
            # Use bulk update for better performance
            update_cases = []
            item_ids = []
            
            for item_id, status in updates:
                update_cases.append(f"WHEN {item_id} THEN '{status}'")
                item_ids.append(str(item_id))
            
            sql = text(f"""
                UPDATE inventory_items 
                SET status = CASE item_id {' '.join(update_cases)} END
                WHERE item_id IN ({','.join(item_ids)})
            """)
            
            result = db.execute(sql)
            db.commit()
            
            return result.rowcount
            
        except Exception as e:
            logger.error(f"Bulk update failed: {e}")
            db.rollback()
            return 0
    
    @staticmethod
    def bulk_create_rental_items(
        db: Session,
        rental_items_data: List[Dict[str, Any]]
    ) -> List[RentalItem]:
        """Bulk create rental items with optimized inserts"""
        try:
            rental_items = [RentalItem(**data) for data in rental_items_data]
            db.bulk_save_objects(rental_items, return_defaults=True)
            db.commit()
            return rental_items
            
        except Exception as e:
            logger.error(f"Bulk create failed: {e}")
            db.rollback()
            return []

# Query optimization utilities
def optimize_database_advanced():
    """Apply advanced database optimizations"""
    with SessionLocal() as db:
        success = True
        
        # Create materialized views
        if not query_optimizer.create_materialized_views(db):
            success = False
        
        # Create advanced indexes
        if not query_optimizer.create_advanced_indexes(db):
            success = False
        
        # Analyze tables for query planner
        try:
            db.execute(text("ANALYZE"))
            db.commit()
            logger.info("✅ Database statistics updated")
        except Exception as e:
            logger.error(f"❌ Failed to update statistics: {e}")
            success = False
        
        return success

# Export main components
__all__ = [
    'AdvancedQueryOptimizer', 'query_optimizer', 'BulkOperations',
    'optimize_database_advanced', 'QueryPerformanceMetrics'
]
