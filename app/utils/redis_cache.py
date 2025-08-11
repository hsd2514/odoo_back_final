"""
Redis Cache Layer Implementation
Provides high-performance caching for frequent database operations
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional, Union, Dict, List
from datetime import datetime, timedelta
import asyncio
from functools import wraps

try:
    import redis
    REDIS_AVAILABLE = True
    try:
        import aioredis
        AIOREDIS_AVAILABLE = True
    except ImportError:
        AIOREDIS_AVAILABLE = False
        aioredis = None
except ImportError:
    REDIS_AVAILABLE = False
    AIOREDIS_AVAILABLE = False
    redis = None
    aioredis = None

from ..config import get_settings

logger = logging.getLogger(__name__)

class RedisCache:
    """High-performance Redis caching layer"""
    
    def __init__(self):
        self.enabled = REDIS_AVAILABLE
        self.redis_client = None
        self.async_redis = None
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
        
        if self.enabled:
            try:
                # Sync Redis client
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # Test connection
                self.redis_client.ping()
                logger.info("✅ Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️ Redis not available: {e}")
                self.enabled = False
    
    async def get_async_client(self):
        """Get async Redis client"""
        if not self.enabled or not AIOREDIS_AVAILABLE:
            return None
            
        if self.async_redis is None:
            try:
                if aioredis:
                    self.async_redis = await aioredis.from_url(
                        "redis://localhost:6379",
                        decode_responses=True,
                        retry_on_timeout=True
                    )
            except Exception as e:
                logger.warning(f"⚠️ Async Redis not available: {e}")
                return None
        return self.async_redis
    
    def _serialize_key(self, key: str) -> str:
        """Create a standardized cache key"""
        return f"odoo_rental:{key}"
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for Redis storage"""
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str)
        return str(value)
    
    def _deserialize_value(self, value: str) -> Any:
        """Deserialize value from Redis"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            cache_key = self._serialize_key(key)
            value = self.redis_client.get(cache_key)
            if value is not None:
                self.cache_stats["hits"] += 1
                return self._deserialize_value(value)
            else:
                self.cache_stats["misses"] += 1
                return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL (default 1 hour)"""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            cache_key = self._serialize_key(key)
            serialized_value = self._serialize_value(value)
            result = self.redis_client.setex(cache_key, ttl, serialized_value)
            if result:
                self.cache_stats["sets"] += 1
            return result
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            cache_key = self._serialize_key(key)
            result = self.redis_client.delete(cache_key)
            if result:
                self.cache_stats["deletes"] += 1
            return bool(result)
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern"""
        if not self.enabled or not self.redis_client:
            return 0
        
        try:
            pattern_key = self._serialize_key(pattern)
            keys = self.redis_client.keys(pattern_key)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache invalidate error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        stats = {
            "enabled": self.enabled,
            "hit_rate": f"{hit_rate:.1f}%",
            "total_requests": total_requests,
            **self.cache_stats
        }
        
        if self.enabled and self.redis_client:
            try:
                info = self.redis_client.info()
                stats.update({
                    "memory_used": info.get("used_memory_human", "N/A"),
                    "connected_clients": info.get("connected_clients", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                })
            except Exception:
                pass
        
        return stats

# Global cache instance
cache = RedisCache()

def cached(ttl: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            if args:
                key_parts.extend([str(arg) for arg in args])
            if kwargs:
                key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            
            cache_key = ":".join(filter(None, key_parts))
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

# Specific cache managers for different data types
class UserCache:
    """User-specific caching"""
    
    @staticmethod
    def get_user_sessions(user_id: int) -> Optional[List[Dict]]:
        return cache.get(f"user_sessions:{user_id}")
    
    @staticmethod
    def set_user_sessions(user_id: int, sessions: List[Dict], ttl: int = 1800):
        cache.set(f"user_sessions:{user_id}", sessions, ttl)
    
    @staticmethod
    def invalidate_user(user_id: int):
        cache.invalidate_pattern(f"user*:{user_id}*")

class ProductCache:
    """Product catalog caching"""
    
    @staticmethod
    def get_product_list(filters: str = "") -> Optional[List[Dict]]:
        return cache.get(f"products:list:{filters}")
    
    @staticmethod
    def set_product_list(filters: str, products: List[Dict], ttl: int = 600):
        cache.set(f"products:list:{filters}", products, ttl)
    
    @staticmethod
    def get_product_detail(product_id: int) -> Optional[Dict]:
        return cache.get(f"product:detail:{product_id}")
    
    @staticmethod
    def set_product_detail(product_id: int, product: Dict, ttl: int = 1800):
        cache.set(f"product:detail:{product_id}", product, ttl)
    
    @staticmethod
    def invalidate_product(product_id: int):
        cache.invalidate_pattern(f"product*:{product_id}*")
        cache.invalidate_pattern("products:list:*")

class InventoryCache:
    """Inventory status caching"""
    
    @staticmethod
    def get_availability(product_id: int, date_range: str) -> Optional[Dict]:
        return cache.get(f"availability:{product_id}:{date_range}")
    
    @staticmethod
    def set_availability(product_id: int, date_range: str, availability: Dict, ttl: int = 300):
        cache.set(f"availability:{product_id}:{date_range}", availability, ttl)
    
    @staticmethod
    def invalidate_inventory(product_id: int):
        cache.invalidate_pattern(f"availability:{product_id}*")
        cache.invalidate_pattern(f"inventory*:{product_id}*")

class SearchCache:
    """Search result caching"""
    
    @staticmethod
    def get_search_results(query: str, filters: str = "") -> Optional[List[Dict]]:
        cache_key = f"search:{hash(query + filters)}"
        return cache.get(cache_key)
    
    @staticmethod
    def set_search_results(query: str, filters: str, results: List[Dict], ttl: int = 1800):
        cache_key = f"search:{hash(query + filters)}"
        cache.set(cache_key, results, ttl)

# Rate limiting using Redis
class RateLimiter:
    """Redis-based rate limiting"""
    
    @staticmethod
    def check_rate_limit(identifier: str, limit: int = 100, window: int = 3600) -> bool:
        """Check if identifier is within rate limit"""
        if not cache.enabled:
            return True
        
        try:
            key = f"rate_limit:{identifier}"
            current = cache.redis_client.get(key)
            
            if current is None:
                cache.redis_client.setex(key, window, 1)
                return True
            
            if int(current) >= limit:
                return False
            
            cache.redis_client.incr(key)
            return True
        except Exception:
            return True  # Allow on error

# Cache warming utilities
async def warm_cache():
    """Pre-populate cache with frequently accessed data"""
    if not cache.enabled:
        return
    
    logger.info("🔥 Starting cache warming...")
    
    try:
        from ..database_optimized import SessionLocal
        from ..models.catalog import Product
        from ..models.user import User
        
        with SessionLocal() as db:
            # Warm product cache
            products = db.query(Product).filter(Product.active == True).limit(50).all()
            for product in products:
                product_dict = {
                    "product_id": product.product_id,
                    "title": product.title,
                    "base_price": float(product.base_price),
                    "pricing_unit": product.pricing_unit,
                    "active": product.active
                }
                ProductCache.set_product_detail(product.product_id, product_dict)
            
            logger.info(f"✅ Warmed cache for {len(products)} products")
    
    except Exception as e:
        logger.warning(f"⚠️ Cache warming failed: {e}")

# Export cache utilities
__all__ = [
    'cache', 'cached', 'UserCache', 'ProductCache', 
    'InventoryCache', 'SearchCache', 'RateLimiter', 'warm_cache'
]
