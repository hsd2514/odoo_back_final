"""
Advanced Redis Database Implementation
=====================================

Complete Redis integration for session management, query caching, 
real-time data, and advanced database operations.
"""

import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
import hashlib
import pickle
from functools import wraps
import uuid

try:
    import redis
    REDIS_AVAILABLE = True
    try:
        import aioredis
        AIOREDIS_AVAILABLE = True
    except ImportError:
        AIOREDIS_AVAILABLE = False
        aioredis = None
        
    try:
        from redis.lock import Lock
    except ImportError:
        # Create a dummy Lock class for fallback
        class Lock:
            def __init__(self, *args, **kwargs):
                pass
            def acquire(self, *args, **kwargs):
                return True
            def release(self):
                pass
except ImportError:
    REDIS_AVAILABLE = False
    AIOREDIS_AVAILABLE = False
    redis = None
    aioredis = None
    # Create a dummy Lock class for fallback
    class Lock:
        def __init__(self, *args, **kwargs):
            pass
        def acquire(self, *args, **kwargs):
            return True
        def release(self):
            pass

logger = logging.getLogger(__name__)

class RedisDatabase:
    """Advanced Redis database operations"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.enabled = REDIS_AVAILABLE
        self.client = None
        self.async_client = None
        self._connection_pool = None
        
        if self.enabled:
            self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialize Redis connections with error handling"""
        try:
            if redis:
                # Create connection pool for better performance
                self._connection_pool = redis.ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=20,
                    retry_on_timeout=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    health_check_interval=30
                )
                
                # Sync client
                self.client = redis.Redis(connection_pool=self._connection_pool)
                self.client.ping()
                
                logger.info("✅ Redis database connections initialized")
        except Exception as e:
            logger.warning(f"⚠️ Redis database unavailable: {e}")
            self.enabled = False
    
    async def get_async_client(self):
        """Get async Redis client"""
        if not self.enabled or not AIOREDIS_AVAILABLE:
            return None
        
        if self.async_client is None:
            try:
                if aioredis:
                    self.async_client = await aioredis.from_url(
                        self.redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                        retry_on_timeout=True,
                        max_connections=20
                    )
            except Exception as e:
                logger.warning(f"⚠️ Async Redis database unavailable: {e}")
                return None
        return self.async_client
    
    def health_check(self) -> Dict[str, Any]:
        """Check Redis database health"""
        if not self.enabled:
            return {"status": "disabled", "message": "Redis not available"}
        
        try:
            start_time = datetime.now()
            if self.client:
                info = self.client.info()
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                return {
                    "status": "healthy",
                    "response_time_ms": f"{response_time:.2f}",
                    "version": info.get("redis_version", "unknown"),
                    "memory_used": info.get("used_memory_human", "N/A"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "uptime_seconds": info.get("uptime_in_seconds", 0)
                }
            else:
                return {"status": "error", "message": "No Redis client available"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Session Management with Redis
class RedisSessionManager:
    """Advanced session management using Redis"""
    
    def __init__(self, redis_db: RedisDatabase):
        self.redis_db = redis_db
        self.session_prefix = "session:"
        self.user_sessions_prefix = "user_sessions:"
        self.default_ttl = 86400  # 24 hours
    
    def create_session(self, user_id: int, session_data: Dict[str, Any], 
                      ttl: int = None) -> str:
        """Create a new user session"""
        if not self.redis_db.enabled:
            return str(uuid.uuid4())  # Fallback to UUID
        
        try:
            session_id = str(uuid.uuid4())
            session_key = f"{self.session_prefix}{session_id}"
            
            # Session data with metadata
            full_session_data = {
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat(),
                "ip_address": session_data.get("ip_address"),
                "user_agent": session_data.get("user_agent"),
                "data": session_data
            }
            
            # Store session
            ttl = ttl or self.default_ttl
            if self.redis_db.client:
                self.redis_db.client.setex(
                    session_key, 
                    ttl, 
                    json.dumps(full_session_data, default=str)
                )
                
                # Add to user's session list
                user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
                self.redis_db.client.sadd(user_sessions_key, session_id)
                self.redis_db.client.expire(user_sessions_key, ttl)
            
            logger.info(f"Created session {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            return str(uuid.uuid4())  # Fallback
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        if not self.redis_db.enabled or not self.redis_db.client:
            return None
        
        try:
            session_key = f"{self.session_prefix}{session_id}"
            session_data = self.redis_db.client.get(session_key)
            
            if session_data:
                parsed_data = json.loads(session_data)
                
                # Update last accessed time
                parsed_data["last_accessed"] = datetime.now().isoformat()
                self.redis_db.client.setex(
                    session_key,
                    self.default_ttl,
                    json.dumps(parsed_data, default=str)
                )
                
                return parsed_data
            return None
            
        except Exception as e:
            logger.error(f"Session retrieval failed: {e}")
            return None

# Query Cache with Redis
class RedisQueryCache:
    """Advanced database query caching"""
    
    def __init__(self, redis_db: RedisDatabase):
        self.redis_db = redis_db
        self.query_prefix = "query_cache:"
        self.default_ttl = 3600
    
    def cache_query_result(self, sql: str, params: tuple, result: Any, 
                          ttl: int = None) -> bool:
        """Cache query result"""
        if not self.redis_db.enabled or not self.redis_db.client:
            return False
        
        try:
            query_hash = hashlib.md5(f"{sql}:{str(params)}".encode()).hexdigest()
            query_key = f"{self.query_prefix}{query_hash}"
            ttl = ttl or self.default_ttl
            
            # Store result
            return self.redis_db.client.setex(
                query_key,
                ttl,
                json.dumps(result, default=str)
            )
            
        except Exception as e:
            logger.error(f"Query cache storage failed: {e}")
            return False
    
    def get_cached_query(self, sql: str, params: tuple = None) -> Optional[Any]:
        """Get cached query result"""
        if not self.redis_db.enabled or not self.redis_db.client:
            return None
        
        try:
            query_hash = hashlib.md5(f"{sql}:{str(params)}".encode()).hexdigest()
            query_key = f"{self.query_prefix}{query_hash}"
            
            cached_data = self.redis_db.client.get(query_key)
            if cached_data:
                return json.loads(cached_data)
            return None
            
        except Exception as e:
            logger.error(f"Query cache retrieval failed: {e}")
            return None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get query cache statistics"""
        if not self.redis_db.enabled:
            return {"enabled": False}
        
        try:
            # Count cached queries
            if self.redis_db.client:
                cursor = 0
                total_queries = 0
                
                while True:
                    cursor, keys = self.redis_db.client.scan(
                        cursor,
                        match=f"{self.query_prefix}*",
                        count=100
                    )
                    total_queries += len(keys)
                    
                    if cursor == 0:
                        break
                
                return {
                    "enabled": True,
                    "total_cached_queries": total_queries,
                    "cache_prefix": self.query_prefix
                }
            else:
                return {"enabled": True, "total_cached_queries": 0}
            
        except Exception as e:
            return {"enabled": True, "error": str(e)}

# Real-time with Redis Pub/Sub (simplified)
class RedisRealTime:
    """Real-time data updates using Redis Pub/Sub"""
    
    def __init__(self, redis_db: RedisDatabase):
        self.redis_db = redis_db
        self.channels = {
            "inventory_updates": "inventory:updates",
            "order_updates": "orders:updates", 
            "user_notifications": "users:notifications"
        }
    
    def publish_message(self, channel: str, message: Dict[str, Any]) -> bool:
        """Publish message to channel"""
        if not self.redis_db.enabled or not self.redis_db.client:
            return False
        
        try:
            result = self.redis_db.client.publish(
                channel,
                json.dumps(message, default=str)
            )
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False

# Distributed Locks with Redis (simplified)
class RedisLock:
    """Distributed locking using Redis"""
    
    def __init__(self, redis_db: RedisDatabase):
        self.redis_db = redis_db
        self.lock_prefix = "lock:"
    
    def acquire_lock(self, resource: str, timeout: int = 60) -> Optional[Lock]:
        """Acquire a distributed lock"""
        if not self.redis_db.enabled or not self.redis_db.client:
            return Lock()  # Return dummy lock
        
        try:
            lock_key = f"{self.lock_prefix}{resource}"
            lock = Lock(self.redis_db.client, lock_key, timeout=timeout)
            
            if lock.acquire(blocking=False):
                return lock
            return None
            
        except Exception as e:
            logger.error(f"Failed to acquire lock for {resource}: {e}")
            return Lock()  # Return dummy lock
    
    def release_lock(self, lock: Lock) -> bool:
        """Release a distributed lock"""
        if not lock:
            return True
        
        try:
            lock.release()
            return True
        except Exception as e:
            logger.error(f"Failed to release lock: {e}")
            return False

# Global Redis database instance
redis_db = RedisDatabase()
session_manager = RedisSessionManager(redis_db)
query_cache = RedisQueryCache(redis_db)
realtime = RedisRealTime(redis_db)
redis_lock = RedisLock(redis_db)

# Decorator for automatic query caching
def cache_database_query(ttl: int = 3600):
    """Decorator to automatically cache database queries"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function and arguments
            func_signature = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Try to get from cache first
            cached_result = query_cache.get_cached_query(func_signature, ())
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache the result
            query_cache.cache_query_result(
                func_signature, 
                (), 
                result, 
                ttl=ttl
            )
            
            logger.debug(f"Cached result for {func.__name__}")
            return result
        
        return wrapper
    return decorator

# Export all Redis database utilities
__all__ = [
    'redis_db', 'session_manager', 'query_cache', 'realtime', 'redis_lock',
    'RedisDatabase', 'RedisSessionManager', 'RedisQueryCache', 
    'RedisRealTime', 'RedisLock', 'cache_database_query'
]
