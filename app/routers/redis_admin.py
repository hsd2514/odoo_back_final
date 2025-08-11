"""
Redis Administration Dashboard
==============================

Complete Redis management interface with monitoring, configuration,
caching controls, and real-time statistics.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta

from ..utils.redis_database import (
    redis_db, session_manager, query_cache, realtime, redis_lock
)
from ..utils.redis_session_manager import (
    redis_session_manager, connection_pool_manager, bulk_operations
)
from ..utils.redis_realtime import (
    ws_manager, live_inventory, live_orders, live_notifications, live_pricing
)
from ..utils.redis_config import (
    redis_config, cluster_manager, sentinel_manager, monitoring, backup_manager
)
from ..utils.redis_cache import cache, UserCache, ProductCache, InventoryCache, SearchCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/redis", tags=["Redis Administration"])

# === Redis Status and Health ===

@router.get("/health", summary="Redis Health Check")
async def redis_health_check():
    """Comprehensive Redis health check"""
    
    health_data = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "unknown",
        "components": {}
    }
    
    # Core Redis database
    if redis_db.enabled:
        health_data["components"]["database"] = redis_db.health_check()
    else:
        health_data["components"]["database"] = {
            "status": "disabled",
            "message": "Redis database not available"
        }
    
    # Cache system
    cache_stats = cache.get_stats()
    health_data["components"]["cache"] = {
        "status": "enabled" if cache.enabled else "disabled",
        "stats": cache_stats
    }
    
    # Session management
    session_stats = redis_session_manager.get_session_stats()
    health_data["components"]["sessions"] = {
        "status": "active",
        "stats": session_stats
    }
    
    # Connection pool
    pool_status = connection_pool_manager.get_pool_status()
    health_data["components"]["connection_pool"] = {
        "status": "active",
        "pool_info": pool_status
    }
    
    # WebSocket management
    if ws_manager:
        ws_stats = ws_manager.get_connection_stats()
        health_data["components"]["websockets"] = {
            "status": "enabled",
            "stats": ws_stats
        }
    else:
        health_data["components"]["websockets"] = {
            "status": "disabled",
            "message": "WebSocket support not available"
        }
    
    # Monitoring
    if monitoring:
        monitor_health = monitoring.check_health()
        health_data["components"]["monitoring"] = monitor_health
    else:
        health_data["components"]["monitoring"] = {
            "status": "disabled"
        }
    
    # Determine overall status
    statuses = [comp.get("status", "unknown") for comp in health_data["components"].values()]
    
    if "error" in statuses or any("fail" in str(comp) for comp in health_data["components"].values()):
        health_data["overall_status"] = "unhealthy"
    elif "warn" in statuses or "degraded" in statuses:
        health_data["overall_status"] = "degraded"
    elif "enabled" in statuses or "healthy" in statuses:
        health_data["overall_status"] = "healthy"
    else:
        health_data["overall_status"] = "partial"
    
    return health_data

@router.get("/status", summary="Redis Comprehensive Status")
async def redis_comprehensive_status():
    """Get comprehensive Redis status including all components"""
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "redis_enabled": redis_db.enabled,
        "cache_enabled": cache.enabled,
        "configuration": {},
        "performance": {},
        "cluster_info": {},
        "sentinel_info": {},
        "monitoring": {}
    }
    
    # Configuration info
    if redis_config:
        status["configuration"] = {
            "host": redis_config.config["host"],
            "port": redis_config.config["port"],
            "db": redis_config.config["db"],
            "max_connections": redis_config.config["max_connections"],
            "default_ttl": redis_config.config["default_ttl"],
            "use_sentinel": redis_config.config["use_sentinel"],
            "cluster_mode": redis_config.config["cluster_mode"],
            "ssl_enabled": redis_config.config["ssl"]
        }
    
    # Performance metrics
    if monitoring:
        performance_summary = monitoring.get_performance_summary()
        status["performance"] = performance_summary
    
    # Cluster information
    if cluster_manager:
        cluster_info = cluster_manager.get_cluster_info()
        status["cluster_info"] = cluster_info
    
    # Sentinel information
    if sentinel_manager:
        sentinel_info = sentinel_manager.get_master_info()
        status["sentinel_info"] = sentinel_info
    
    return status

# === Cache Management ===

@router.get("/cache/stats", summary="Cache Statistics")
async def get_cache_statistics():
    """Get detailed cache statistics"""
    
    stats = {
        "timestamp": datetime.now().isoformat(),
        "overall": cache.get_stats(),
        "query_cache": {},
        "session_cache": {},
        "specialized_caches": {}
    }
    
    # Query cache stats
    if query_cache:
        stats["query_cache"] = query_cache.get_cache_stats()
    
    # Session stats
    stats["session_cache"] = redis_session_manager.get_session_stats()
    
    # Get stats for specialized caches (simulated)
    stats["specialized_caches"] = {
        "user_cache": {"status": "active", "estimated_entries": "~100"},
        "product_cache": {"status": "active", "estimated_entries": "~500"},
        "inventory_cache": {"status": "active", "estimated_entries": "~200"},
        "search_cache": {"status": "active", "estimated_entries": "~50"}
    }
    
    return stats

@router.post("/cache/warm", summary="Warm Cache")
async def warm_cache_manually(background_tasks: BackgroundTasks):
    """Manually trigger cache warming"""
    
    if not cache.enabled:
        raise HTTPException(status_code=503, detail="Cache not available")
    
    try:
        # Import and call cache warming function
        from ..utils.redis_cache import warm_cache
        background_tasks.add_task(warm_cache)
        
        return {
            "status": "success",
            "message": "Cache warming initiated in background",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Cache warming failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cache warming failed: {str(e)}")

@router.delete("/cache/clear", summary="Clear Cache")
async def clear_cache(
    cache_type: Optional[str] = None,
    pattern: Optional[str] = None
):
    """Clear cache data"""
    
    if not cache.enabled:
        raise HTTPException(status_code=503, detail="Cache not available")
    
    try:
        cleared_count = 0
        
        if pattern:
            # Clear by pattern
            cleared_count = cache.invalidate_pattern(pattern)
            message = f"Cleared {cleared_count} cache entries matching pattern: {pattern}"
        
        elif cache_type:
            # Clear specific cache type
            if cache_type == "products":
                ProductCache.invalidate_product("*")
                message = "Cleared product cache"
            elif cache_type == "users":
                UserCache.invalidate_user("*")
                message = "Cleared user cache"
            elif cache_type == "inventory":
                InventoryCache.invalidate_inventory("*")
                message = "Cleared inventory cache"
            elif cache_type == "queries":
                if query_cache:
                    query_cache.invalidate_by_tags(["*"])
                message = "Cleared query cache"
            else:
                raise HTTPException(status_code=400, detail="Invalid cache type")
        
        else:
            # Clear all cache (dangerous operation)
            if redis_db.enabled and redis_db.client:
                redis_db.client.flushdb()
                message = "Cleared entire cache database"
            else:
                raise HTTPException(status_code=503, detail="Cannot clear cache - Redis not available")
        
        return {
            "status": "success",
            "message": message,
            "cleared_count": cleared_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cache clearing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cache clearing failed: {str(e)}")

# === Session Management ===

@router.get("/sessions/stats", summary="Session Statistics")
async def get_session_statistics():
    """Get session management statistics"""
    
    stats = redis_session_manager.get_session_stats()
    
    # Add session manager specific stats
    if session_manager and redis_db.enabled:
        try:
            # Count active sessions
            cursor = 0
            session_count = 0
            
            while True:
                cursor, keys = redis_db.client.scan(
                    cursor,
                    match="session:*",
                    count=100
                )
                session_count += len(keys)
                
                if cursor == 0:
                    break
            
            stats["active_sessions"] = session_count
            
        except Exception as e:
            logger.error(f"Failed to count sessions: {e}")
            stats["active_sessions"] = "unknown"
    
    return {
        "timestamp": datetime.now().isoformat(),
        "stats": stats
    }

@router.post("/sessions/cleanup", summary="Clean Up Expired Sessions")
async def cleanup_expired_sessions():
    """Clean up expired sessions"""
    
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not available")
    
    try:
        cleaned_count = session_manager.cleanup_expired_sessions()
        
        return {
            "status": "success",
            "cleaned_sessions": cleaned_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Session cleanup failed: {str(e)}")

# === Real-time Features ===

@router.get("/realtime/stats", summary="Real-time Feature Statistics")
async def get_realtime_statistics():
    """Get real-time feature statistics"""
    
    if not ws_manager:
        return {
            "status": "disabled",
            "message": "WebSocket support not available"
        }
    
    stats = ws_manager.get_connection_stats()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "websocket_enabled": ws_manager is not None,
        "redis_pubsub_enabled": realtime is not None and redis_db.enabled,
        "stats": stats
    }

@router.post("/realtime/test", summary="Test Real-time Messaging")
async def test_realtime_messaging(
    message_type: str = "test",
    test_data: Dict[str, Any] = {"message": "Test notification"}
):
    """Test real-time messaging system"""
    
    if not ws_manager:
        raise HTTPException(status_code=503, detail="WebSocket support not available")
    
    try:
        # Send test message based on type
        if message_type == "inventory":
            if live_inventory:
                await live_inventory.update_product_availability(
                    product_id=999,
                    availability_data={"available": True, "test": True, **test_data}
                )
        elif message_type == "notification":
            if live_notifications:
                await live_notifications.send_notification(
                    user_id=1,
                    notification={"type": "test", **test_data}
                )
        elif message_type == "price":
            if live_pricing:
                await live_pricing.update_product_price(
                    product_id=999,
                    new_price=99.99
                )
        else:
            # Generic broadcast
            await ws_manager.broadcast_to_channel(
                "test_channel",
                {"type": "test", "data": test_data, "timestamp": datetime.now().isoformat()}
            )
        
        return {
            "status": "success",
            "message": f"Test {message_type} message sent",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Real-time test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Real-time test failed: {str(e)}")

# === Configuration Management ===

@router.get("/config", summary="Redis Configuration")
async def get_redis_configuration():
    """Get current Redis configuration"""
    
    if not redis_config:
        raise HTTPException(status_code=503, detail="Redis configuration not available")
    
    # Return safe configuration (no passwords)
    safe_config = dict(redis_config.config)
    safe_config.pop("password", None)
    safe_config.pop("ssl_keyfile", None)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "configuration": safe_config,
        "connection_url": redis_config.get_redis_url().replace(
            redis_config.config.get("password", ""), "***"
        ) if redis_config.config.get("password") else redis_config.get_redis_url()
    }

@router.get("/config/optimize", summary="Configuration Optimization Recommendations")
async def get_optimization_recommendations():
    """Get Redis configuration optimization recommendations"""
    
    recommendations = []
    current_config = redis_config.config if redis_config else {}
    
    # Memory optimization
    if monitoring:
        performance = monitoring.get_performance_summary()
        latest_metrics = performance.get("latest_metrics", {})
        
        memory_info = latest_metrics.get("memory", {})
        used_memory = memory_info.get("used_memory", 0)
        max_memory = memory_info.get("maxmemory", 0)
        
        if max_memory == 0:
            recommendations.append({
                "category": "memory",
                "priority": "medium",
                "recommendation": "Set maxmemory limit to prevent Redis from using too much RAM",
                "suggested_value": "512MB or based on available system memory"
            })
        
        elif used_memory > max_memory * 0.8:
            recommendations.append({
                "category": "memory",
                "priority": "high",
                "recommendation": "Memory usage is high - consider increasing maxmemory or enabling key eviction",
                "current_usage": f"{used_memory / 1024 / 1024:.1f}MB / {max_memory / 1024 / 1024:.1f}MB"
            })
    
    # Connection pool optimization
    if connection_pool_manager:
        pool_optimization = connection_pool_manager.optimize_pool_settings()
        if pool_optimization.get("recommendations"):
            for rec in pool_optimization["recommendations"]:
                recommendations.append({
                    "category": "connection_pool",
                    "priority": "medium",
                    "recommendation": rec,
                    "optimal_settings": pool_optimization.get("optimal_settings", {})
                })
    
    # SSL recommendation
    if not current_config.get("ssl", False):
        recommendations.append({
            "category": "security",
            "priority": "medium",
            "recommendation": "Consider enabling SSL/TLS for production deployments",
            "suggested_action": "Set REDIS_SSL=true and configure certificates"
        })
    
    # Persistence recommendation
    if monitoring:
        latest_metrics = monitoring.metrics_history[-1] if monitoring.metrics_history else {}
        persistence_info = latest_metrics.get("persistence", {})
        
        if not persistence_info.get("aof_enabled", False):
            recommendations.append({
                "category": "persistence",
                "priority": "low", 
                "recommendation": "Consider enabling AOF persistence for better durability",
                "suggested_action": "Configure appendonly yes in Redis configuration"
            })
    
    return {
        "timestamp": datetime.now().isoformat(),
        "total_recommendations": len(recommendations),
        "recommendations": recommendations
    }

# === Backup Management ===

@router.post("/backup/create", summary="Create Redis Backup")
async def create_redis_backup():
    """Create a Redis backup"""
    
    if not backup_manager:
        raise HTTPException(status_code=503, detail="Backup manager not available")
    
    try:
        backup_result = backup_manager.create_backup()
        
        if backup_result["status"] == "success":
            return backup_result
        else:
            raise HTTPException(status_code=500, detail=backup_result["message"])
            
    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backup creation failed: {str(e)}")

@router.get("/backup/list", summary="List Redis Backups")
async def list_redis_backups():
    """List available Redis backups"""
    
    if not backup_manager:
        raise HTTPException(status_code=503, detail="Backup manager not available")
    
    try:
        backups = backup_manager.list_backups()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "backup_count": len(backups),
            "backups": backups
        }
        
    except Exception as e:
        logger.error(f"Backup listing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backup listing failed: {str(e)}")

@router.delete("/backup/cleanup", summary="Clean Up Old Backups")
async def cleanup_old_backups():
    """Clean up old backups based on retention policy"""
    
    if not backup_manager:
        raise HTTPException(status_code=503, detail="Backup manager not available")
    
    try:
        cleaned_count = backup_manager.cleanup_old_backups()
        
        return {
            "status": "success",
            "cleaned_backups": cleaned_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Backup cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backup cleanup failed: {str(e)}")

# === Monitoring and Metrics ===

@router.get("/metrics", summary="Redis Metrics")
async def get_redis_metrics():
    """Get comprehensive Redis metrics"""
    
    if not monitoring:
        raise HTTPException(status_code=503, detail="Monitoring not available")
    
    try:
        # Collect current metrics
        current_metrics = monitoring.collect_metrics()
        
        # Get performance summary
        performance_summary = monitoring.get_performance_summary()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "current_metrics": current_metrics,
            "performance_summary": performance_summary,
            "monitoring_enabled": True
        }
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics collection failed: {str(e)}")

@router.get("/metrics/history", summary="Redis Metrics History")
async def get_metrics_history(hours: int = 1):
    """Get Redis metrics history"""
    
    if not monitoring:
        raise HTTPException(status_code=503, detail="Monitoring not available")
    
    # Get recent metrics
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    recent_metrics = []
    for metric in monitoring.metrics_history:
        metric_time = datetime.fromisoformat(metric["timestamp"])
        if metric_time >= cutoff_time:
            recent_metrics.append(metric)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "hours_requested": hours,
        "metrics_count": len(recent_metrics),
        "metrics": recent_metrics
    }

# === Administrative Operations ===

@router.post("/admin/reset", summary="Reset Redis (Dangerous)")
async def reset_redis_database(confirm: bool = False):
    """Reset Redis database (DANGEROUS - removes all data)"""
    
    if not confirm:
        return {
            "status": "confirmation_required",
            "message": "This operation will delete ALL Redis data",
            "warning": "Set confirm=true to proceed",
            "timestamp": datetime.now().isoformat()
        }
    
    if not redis_db.enabled or not redis_db.client:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    try:
        # Flush the database
        redis_db.client.flushdb()
        
        # Reset statistics
        if monitoring:
            monitoring.metrics_history.clear()
        
        redis_session_manager.stats = {
            "sessions_created": 0,
            "sessions_cached": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "queries_executed": 0,
            "queries_cached": 0,
            "connection_pool_usage": 0
        }
        
        logger.warning("Redis database was reset - all data lost")
        
        return {
            "status": "success",
            "message": "Redis database has been reset",
            "warning": "ALL DATA WAS DELETED",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Redis reset failed: {e}")
        raise HTTPException(status_code=500, detail=f"Redis reset failed: {str(e)}")

@router.get("/admin/info", summary="Administrative Information")
async def get_admin_info():
    """Get administrative information about Redis setup"""
    
    info = {
        "timestamp": datetime.now().isoformat(),
        "components": {
            "redis_database": redis_db.enabled,
            "cache_system": cache.enabled,
            "session_manager": session_manager is not None,
            "query_cache": query_cache is not None,
            "realtime_features": realtime is not None,
            "websocket_manager": ws_manager is not None,
            "monitoring": monitoring is not None,
            "backup_manager": backup_manager is not None,
            "cluster_support": cluster_manager is not None,
            "sentinel_support": sentinel_manager is not None
        },
        "configuration": {
            "redis_available": redis_db.enabled,
            "host": redis_config.config["host"] if redis_config else "unknown",
            "port": redis_config.config["port"] if redis_config else "unknown",
            "ssl_enabled": redis_config.config["ssl"] if redis_config else False,
            "cluster_mode": redis_config.config["cluster_mode"] if redis_config else False,
            "sentinel_mode": redis_config.config["use_sentinel"] if redis_config else False
        },
        "endpoints": [
            "/redis/health - Health check",
            "/redis/status - Comprehensive status",
            "/redis/cache/stats - Cache statistics",
            "/redis/sessions/stats - Session statistics", 
            "/redis/realtime/stats - Real-time feature statistics",
            "/redis/metrics - Performance metrics",
            "/redis/config - Configuration info",
            "/redis/backup/list - Available backups"
        ]
    }
    
    return info

# Export the router
__all__ = ["router"]
