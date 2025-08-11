"""
Redis-Optimized Database Session Management
==========================================

Advanced database session management with Redis integration for
connection pooling, transaction caching, and optimized query execution.
"""

import logging
from typing import Any, Dict, List, Optional, Generator, Callable
from contextlib import contextmanager, asynccontextmanager
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy import event, text
from datetime import datetime, timedelta
import threading
import time
import uuid

from .redis_database import redis_db, query_cache, session_manager, redis_lock
from ..database_optimized import engine, SessionLocal

logger = logging.getLogger(__name__)

class RedisOptimizedSessionManager:
    """Advanced session management with Redis optimization"""
    
    def __init__(self):
        self.local_storage = threading.local()
        self.session_factory = SessionLocal
        self.stats = {
            "sessions_created": 0,
            "sessions_cached": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "queries_executed": 0,
            "queries_cached": 0,
            "connection_pool_usage": 0
        }
        
        # Setup query event listeners for automatic caching
        self._setup_query_listeners()
    
    def _setup_query_listeners(self):
        """Setup SQLAlchemy event listeners for automatic query optimization"""
        
        @event.listens_for(Engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log and potentially cache queries"""
            context._query_start_time = time.time()
            
            # Check if this is a SELECT query that can be cached
            if statement.strip().upper().startswith('SELECT'):
                # Try to get from cache first
                cache_key = f"{statement}:{str(parameters)}"
                cached_result = query_cache.get_cached_query(statement, parameters)
                
                if cached_result is not None:
                    self.stats["cache_hits"] += 1
                    context._cached_result = cached_result
                else:
                    self.stats["cache_misses"] += 1
        
        @event.listens_for(Engine, "after_cursor_execute") 
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log query execution time and cache results"""
            total_time = time.time() - context._query_start_time
            self.stats["queries_executed"] += 1
            
            # Cache SELECT query results if they took significant time
            if (statement.strip().upper().startswith('SELECT') 
                and total_time > 0.1  # Cache queries that take > 100ms
                and not hasattr(context, '_cached_result')):
                
                try:
                    # Cache the result for future use
                    result_data = cursor.fetchall() if hasattr(cursor, 'fetchall') else None
                    if result_data:
                        query_cache.cache_query_result(
                            statement, 
                            parameters, 
                            result_data,
                            ttl=300,  # 5 minutes for expensive queries
                            tags=self._extract_table_tags(statement)
                        )
                        self.stats["queries_cached"] += 1
                except Exception as e:
                    logger.debug(f"Could not cache query result: {e}")
            
            # Log slow queries
            if total_time > 1.0:  # Log queries taking > 1 second
                logger.warning(f"Slow query ({total_time:.2f}s): {statement[:100]}...")
    
    def _extract_table_tags(self, sql: str) -> List[str]:
        """Extract table names from SQL for cache invalidation"""
        try:
            # Simple regex to find table names (improve as needed)
            import re
            # Look for FROM and JOIN clauses
            table_pattern = r'(?:FROM|JOIN)\s+(\w+)'
            matches = re.findall(table_pattern, sql.upper())
            return [match.lower() for match in matches]
        except:
            return []
    
    @contextmanager
    def get_db_session(self, use_cache: bool = True) -> Generator[Session, None, None]:
        """Get database session with Redis optimization"""
        session = None
        session_id = None
        
        try:
            # Check if we have a session in local storage (request-scoped)
            if hasattr(self.local_storage, 'session') and self.local_storage.session:
                session = self.local_storage.session
                self.stats["sessions_cached"] += 1
            else:
                # Create new session
                session = self.session_factory()
                self.local_storage.session = session
                self.stats["sessions_created"] += 1
                
                # Store session info in Redis for monitoring
                if redis_db.enabled and use_cache:
                    session_id = str(uuid.uuid4())
                    session_info = {
                        "created_at": datetime.now().isoformat(),
                        "thread_id": threading.get_ident(),
                        "connection_info": str(session.bind)
                    }
                    redis_db.client.setex(
                        f"db_session:{session_id}",
                        3600,  # 1 hour
                        str(session_info)
                    )
            
            yield session
            
            # Commit transaction
            session.commit()
            
        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            # Clean up Redis session info
            if session_id and redis_db.enabled:
                try:
                    redis_db.client.delete(f"db_session:{session_id}")
                except:
                    pass
            
            # Keep session in local storage for reuse within request
            # Session will be closed when request ends
    
    def close_local_session(self):
        """Close the local thread session"""
        if hasattr(self.local_storage, 'session') and self.local_storage.session:
            try:
                self.local_storage.session.close()
            except:
                pass
            finally:
                self.local_storage.session = None
    
    @contextmanager
    def get_db_transaction(self, isolation_level: str = None) -> Generator[Session, None, None]:
        """Get database session with specific transaction isolation"""
        with self.get_db_session() as session:
            if isolation_level:
                session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
            
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
    
    def execute_with_cache(self, query: str, params: Dict[str, Any] = None, 
                          ttl: int = 300, tags: List[str] = None) -> List[Dict[str, Any]]:
        """Execute query with Redis caching"""
        
        # Try cache first
        cache_key = f"{query}:{str(params) if params else ''}"
        cached_result = query_cache.get_cached_query(query, tuple(params.values()) if params else ())
        
        if cached_result is not None:
            self.stats["cache_hits"] += 1
            return cached_result
        
        # Execute query
        with self.get_db_session() as session:
            result = session.execute(text(query), params or {})
            rows = result.fetchall()
            
            # Convert to list of dicts
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in rows]
            
            # Cache result
            query_cache.cache_query_result(
                query,
                tuple(params.values()) if params else (),
                data,
                ttl=ttl,
                tags=tags
            )
            
            self.stats["cache_misses"] += 1
            return data
    
    def invalidate_cache_by_tables(self, table_names: List[str]):
        """Invalidate cache for specific tables"""
        query_cache.invalidate_by_tags(table_names)
        logger.info(f"Invalidated cache for tables: {table_names}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session management statistics"""
        base_stats = dict(self.stats)
        
        # Add Redis-specific stats if available
        if redis_db.enabled:
            try:
                redis_stats = redis_db.health_check()
                base_stats["redis_status"] = redis_stats.get("status", "unknown")
                base_stats["redis_memory"] = redis_stats.get("memory_used", "N/A")
            except:
                base_stats["redis_status"] = "error"
        else:
            base_stats["redis_status"] = "disabled"
        
        # Calculate efficiency metrics
        total_sessions = base_stats["sessions_created"] + base_stats["sessions_cached"]
        if total_sessions > 0:
            base_stats["session_reuse_rate"] = f"{(base_stats['sessions_cached'] / total_sessions * 100):.1f}%"
        
        total_cache_ops = base_stats["cache_hits"] + base_stats["cache_misses"]
        if total_cache_ops > 0:
            base_stats["cache_hit_rate"] = f"{(base_stats['cache_hits'] / total_cache_ops * 100):.1f}%"
        
        return base_stats

# Connection Pool Optimization with Redis
class RedisConnectionPoolManager:
    """Manage database connections with Redis coordination"""
    
    def __init__(self, max_connections: int = 20, max_overflow: int = 10):
        self.max_connections = max_connections
        self.max_overflow = max_overflow
        self.pool_stats = {
            "active_connections": 0,
            "pool_size": 0,
            "overflow_connections": 0,
            "total_requests": 0
        }
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status"""
        try:
            # Get SQLAlchemy pool stats
            pool = engine.pool
            
            status = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalidated": pool.invalidated(),
                "max_connections": self.max_connections,
                "max_overflow": self.max_overflow
            }
            
            # Store in Redis for monitoring
            if redis_db.enabled:
                redis_db.client.setex(
                    "db_pool_status",
                    60,  # 1 minute TTL
                    str(status)
                )
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get pool status: {e}")
            return {"error": str(e)}
    
    def optimize_pool_settings(self) -> Dict[str, Any]:
        """Analyze and suggest pool optimizations"""
        status = self.get_pool_status()
        
        recommendations = []
        
        # Check utilization
        if "checked_out" in status and "size" in status:
            utilization = (status["checked_out"] / status["size"]) * 100 if status["size"] > 0 else 0
            
            if utilization > 80:
                recommendations.append("Consider increasing pool size - high utilization detected")
            elif utilization < 20:
                recommendations.append("Pool size may be too large - low utilization detected")
        
        # Check overflow usage
        if status.get("overflow", 0) > 0:
            recommendations.append("Overflow connections in use - consider increasing base pool size")
        
        return {
            "current_status": status,
            "recommendations": recommendations,
            "optimal_settings": {
                "pool_size": max(5, min(20, status.get("checked_out", 0) + 5)),
                "max_overflow": max(0, status.get("overflow", 0) + 3)
            }
        }

# Bulk Operations with Redis Coordination
class RedisBulkOperations:
    """Optimized bulk database operations with Redis coordination"""
    
    def __init__(self, session_manager: RedisOptimizedSessionManager):
        self.session_manager = session_manager
    
    def bulk_insert_with_cache_invalidation(self, model_class, data_list: List[Dict[str, Any]], 
                                          batch_size: int = 1000) -> int:
        """Bulk insert with automatic cache invalidation"""
        
        # Use distributed lock to prevent cache inconsistency
        table_name = model_class.__tablename__
        lock = redis_lock.acquire_lock(f"bulk_insert:{table_name}", timeout=300)
        
        try:
            inserted_count = 0
            
            with self.session_manager.get_db_transaction() as session:
                # Process in batches
                for i in range(0, len(data_list), batch_size):
                    batch = data_list[i:i + batch_size]
                    
                    # Bulk insert
                    session.bulk_insert_mappings(model_class, batch)
                    inserted_count += len(batch)
                    
                    # Flush every batch
                    session.flush()
                
                # Commit all changes
                session.commit()
            
            # Invalidate related caches
            self.session_manager.invalidate_cache_by_tables([table_name])
            
            logger.info(f"Bulk inserted {inserted_count} records into {table_name}")
            return inserted_count
            
        finally:
            if lock:
                redis_lock.release_lock(lock)
    
    def bulk_update_with_cache_invalidation(self, model_class, updates: List[Dict[str, Any]],
                                          batch_size: int = 1000) -> int:
        """Bulk update with automatic cache invalidation"""
        
        table_name = model_class.__tablename__
        lock = redis_lock.acquire_lock(f"bulk_update:{table_name}", timeout=300)
        
        try:
            updated_count = 0
            
            with self.session_manager.get_db_transaction() as session:
                # Process in batches
                for i in range(0, len(updates), batch_size):
                    batch = updates[i:i + batch_size]
                    
                    # Bulk update
                    session.bulk_update_mappings(model_class, batch)
                    updated_count += len(batch)
                    
                    # Flush every batch
                    session.flush()
                
                # Commit all changes
                session.commit()
            
            # Invalidate related caches
            self.session_manager.invalidate_cache_by_tables([table_name])
            
            logger.info(f"Bulk updated {updated_count} records in {table_name}")
            return updated_count
            
        finally:
            if lock:
                redis_lock.release_lock(lock)

# Global instances
redis_session_manager = RedisOptimizedSessionManager()
connection_pool_manager = RedisConnectionPoolManager()
bulk_operations = RedisBulkOperations(redis_session_manager)

# Decorator for automatic session management
def with_redis_session(use_cache: bool = True, isolation_level: str = None):
    """Decorator for automatic Redis-optimized session management"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if isolation_level:
                with redis_session_manager.get_db_transaction(isolation_level) as session:
                    return func(session, *args, **kwargs)
            else:
                with redis_session_manager.get_db_session(use_cache) as session:
                    return func(session, *args, **kwargs)
        return wrapper
    return decorator

# Context manager for Redis-optimized database operations
@contextmanager
def redis_optimized_db():
    """Context manager for Redis-optimized database operations"""
    try:
        with redis_session_manager.get_db_session() as session:
            yield session
    finally:
        redis_session_manager.close_local_session()

# Export all Redis database session utilities
__all__ = [
    'redis_session_manager', 'connection_pool_manager', 'bulk_operations',
    'RedisOptimizedSessionManager', 'RedisConnectionPoolManager', 
    'RedisBulkOperations', 'with_redis_session', 'redis_optimized_db'
]
