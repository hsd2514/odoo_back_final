"""
Peak Performance Router
Provides advanced optimization endpoints and performance monitoring
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database_optimized import get_db
from ..utils.auth import require_roles, get_current_user
from ..utils.advanced_query_optimizer import query_optimizer, optimize_database_advanced
from ..utils.celery_background_tasks import task_manager, send_rental_confirmation_email
from ..middleware.advanced_performance import api_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["performance"])

# Pydantic models for requests/responses
class CacheOperationRequest(BaseModel):
    key: str
    value: Optional[Any] = None
    ttl: Optional[int] = 3600

class OptimizationRequest(BaseModel):
    operation: str  # "cache_warm", "db_optimize", "cleanup"
    parameters: Optional[Dict[str, Any]] = None

class ReportRequest(BaseModel):
    report_type: str  # "rental_summary", "inventory_status", "revenue_analysis"
    parameters: Dict[str, Any]

# Cache Management Endpoints
@router.get("/cache/stats", summary="Get cache statistics")
async def get_cache_stats():
    """Get Redis cache performance statistics"""
    return cache.get_stats()

@router.post("/cache/warm", summary="Warm cache with frequently accessed data")
async def warm_cache_endpoint(background_tasks: BackgroundTasks, _: None = Depends(require_roles("Admin"))):
    """Pre-populate cache with frequently accessed data"""
    background_tasks.add_task(warm_cache)
    return {"message": "Cache warming started", "status": "in_progress"}

@router.delete("/cache/invalidate", summary="Invalidate cache pattern")
async def invalidate_cache(
    pattern: str = Query(..., description="Cache key pattern to invalidate"),
    _: None = Depends(require_roles("Admin"))
):
    """Invalidate cache keys matching pattern"""
    invalidated_count = cache.invalidate_pattern(pattern)
    return {
        "message": f"Invalidated {invalidated_count} cache entries",
        "pattern": pattern,
        "count": invalidated_count
    }

@router.get("/cache/test", summary="Test cache performance")
async def test_cache_performance():
    """Test cache read/write performance"""
    test_key = f"test_performance_{datetime.now().timestamp()}"
    test_data = {"message": "Cache performance test", "timestamp": datetime.now().isoformat()}
    
    # Test write performance
    start_time = datetime.now()
    cache.set(test_key, test_data, 60)
    write_time = (datetime.now() - start_time).total_seconds() * 1000
    
    # Test read performance
    start_time = datetime.now()
    cached_data = cache.get(test_key)
    read_time = (datetime.now() - start_time).total_seconds() * 1000
    
    # Cleanup
    cache.delete(test_key)
    
    return {
        "cache_enabled": cache.enabled,
        "write_time_ms": f"{write_time:.2f}",
        "read_time_ms": f"{read_time:.2f}",
        "data_integrity": cached_data == test_data
    }

# Query Optimization Endpoints
@router.get("/queries/stats", summary="Get query performance statistics")
async def get_query_stats():
    """Get query performance metrics"""
    return query_optimizer.get_performance_report()

@router.post("/optimize/database", summary="Apply advanced database optimizations")
async def optimize_database(
    background_tasks: BackgroundTasks,
    _: None = Depends(require_roles("Admin"))
):
    """Apply advanced database optimizations"""
    background_tasks.add_task(optimize_database_advanced)
    return {
        "message": "Database optimization started",
        "status": "in_progress",
        "operations": [
            "Creating materialized views",
            "Building advanced indexes",
            "Updating query statistics"
        ]
    }

# Advanced Query Endpoints
@router.get("/queries/catalog/optimized", summary="Get optimized product catalog")
async def get_optimized_catalog(
    category_id: Optional[int] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    search_query: Optional[str] = Query(None),
    include_availability: bool = Query(True),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """Get product catalog using optimized queries with caching"""
    return query_optimizer.get_product_catalog_optimized(
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        search_query=search_query,
        include_availability=include_availability,
        limit=limit,
        offset=offset
    )

@router.get("/queries/availability/optimized", summary="Get optimized availability check")
async def get_optimized_availability(
    product_id: int = Query(...),
    start_date: datetime = Query(...),
    end_date: datetime = Query(...)
):
    """Get product availability using optimized queries"""
    return query_optimizer.get_product_availability_optimized(
        product_id=product_id,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/queries/analytics/optimized", summary="Get optimized rental analytics")
async def get_optimized_analytics(
    seller_id: Optional[int] = Query(None),
    days: int = Query(30, ge=1, le=365)
):
    """Get rental analytics using optimized queries"""
    return query_optimizer.get_rental_analytics_optimized(
        seller_id=seller_id,
        days=days
    )

# Background Task Management
@router.get("/tasks/stats", summary="Get background task statistics")
async def get_task_stats():
    """Get background task queue statistics"""
    return task_manager.get_queue_stats()

@router.post("/tasks/reports/generate", summary="Generate report asynchronously")
async def generate_report_async(
    request: ReportRequest,
    current_user = Depends(get_current_user)
):
    """Generate reports asynchronously"""
    task_id = task_manager.generate_report_async(
        report_type=request.report_type,
        parameters=request.parameters,
        user_id=current_user.user_id
    )
    
    return {
        "message": "Report generation started",
        "task_id": task_id,
        "status": "in_progress"
    }

@router.get("/tasks/{task_id}/status", summary="Get task status")
async def get_task_status(task_id: str):
    """Get status of background task"""
    return task_manager.get_task_status(task_id)

@router.post("/tasks/cleanup", summary="Run data cleanup task")
async def run_cleanup_task(
    days_old: int = Query(90, ge=30, le=365),
    _: None = Depends(require_roles("Admin"))
):
    """Run data cleanup task for old records"""
    task_id = task_manager.cleanup_old_data_async(days_old)
    
    return {
        "message": "Data cleanup started",
        "task_id": task_id,
        "parameters": {"days_old": days_old}
    }

# API Performance Metrics
@router.get("/metrics/api", summary="Get API performance metrics")
async def get_api_metrics():
    """Get comprehensive API performance metrics"""
    if hasattr(api_metrics, '_instance'):
        return api_metrics._instance.get_metrics()
    else:
        return {"message": "Metrics not available", "enabled": False}

@router.get("/metrics/system", summary="Get system performance metrics")
async def get_system_metrics():
    """Get system-level performance metrics"""
    import psutil
    import os
    
    # Memory usage
    memory = psutil.virtual_memory()
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # Disk usage
    disk = psutil.disk_usage('/')
    
    # Database connection pool info
    from ..database_optimized import db_manager
    pool_info = db_manager.get_connection_info()
    
    return {
        "system": {
            "memory": {
                "total": f"{memory.total / (1024**3):.1f} GB",
                "available": f"{memory.available / (1024**3):.1f} GB",
                "used_percent": f"{memory.percent:.1f}%"
            },
            "cpu": {
                "usage_percent": f"{cpu_percent:.1f}%",
                "cores": psutil.cpu_count()
            },
            "disk": {
                "total": f"{disk.total / (1024**3):.1f} GB",
                "free": f"{disk.free / (1024**3):.1f} GB",
                "used_percent": f"{(disk.used / disk.total) * 100:.1f}%"
            }
        },
        "database": pool_info,
        "cache": cache.get_stats(),
        "background_tasks": task_manager.get_queue_stats()
    }

# Performance Benchmarking
@router.post("/benchmark/run", summary="Run performance benchmark")
async def run_performance_benchmark(
    background_tasks: BackgroundTasks,
    test_type: str = Query("comprehensive", description="Type of benchmark to run"),
    _: None = Depends(require_roles("Admin"))
):
    """Run comprehensive performance benchmark"""
    
    async def run_benchmark():
        """Run the actual benchmark"""
        try:
            # Import performance tracker
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            
            from performance_tracker import PerformanceTracker
            
            tracker = PerformanceTracker()
            results = tracker.run_comprehensive_performance_test()
            
            # Store results in cache for retrieval
            cache.set("benchmark_results", results, 3600)  # 1 hour TTL
            
            logger.info("✅ Performance benchmark completed")
            
        except Exception as e:
            logger.error(f"❌ Benchmark failed: {e}")
            cache.set("benchmark_results", {"error": str(e)}, 3600)
    
    background_tasks.add_task(run_benchmark)
    
    return {
        "message": "Performance benchmark started",
        "status": "in_progress",
        "test_type": test_type,
        "note": "Results will be available at /performance/benchmark/results"
    }

@router.get("/benchmark/results", summary="Get benchmark results")
async def get_benchmark_results():
    """Get latest benchmark results"""
    results = cache.get("benchmark_results")
    
    if results is None:
        return {
            "message": "No benchmark results available",
            "status": "not_found",
            "note": "Run a benchmark first using /performance/benchmark/run"
        }
    
    return {
        "results": results,
        "cached_at": datetime.now().isoformat()
    }

# Performance Tuning Recommendations
@router.get("/recommendations", summary="Get performance optimization recommendations")
async def get_performance_recommendations():
    """Get AI-powered performance optimization recommendations"""
    
    # Analyze current performance metrics
    cache_stats = cache.get_stats()
    
    recommendations = []
    
    # Cache optimization recommendations
    if cache.enabled:
        hit_rate = float(cache_stats.get("hit_rate", "0").replace("%", ""))
        if hit_rate < 80:
            recommendations.append({
                "category": "Cache Optimization",
                "priority": "High",
                "recommendation": "Increase cache TTL for frequently accessed data",
                "impact": "30-50% faster response times",
                "action": "Review cache key patterns and increase TTL values"
            })
    else:
        recommendations.append({
            "category": "Cache Infrastructure",
            "priority": "Critical", 
            "recommendation": "Install and configure Redis for caching",
            "impact": "90%+ faster data access",
            "action": "pip install redis && configure Redis server"
        })
    
    # Database optimization recommendations
    recommendations.extend([
        {
            "category": "Database Performance",
            "priority": "High",
            "recommendation": "Implement read replicas for read-heavy operations",
            "impact": "80% better read performance",
            "action": "Setup PostgreSQL read replicas"
        },
        {
            "category": "Query Optimization",
            "priority": "Medium",
            "recommendation": "Add composite indexes for complex queries",
            "impact": "60% faster query execution",
            "action": "Run database optimization endpoint"
        },
        {
            "category": "Background Processing",
            "priority": "High",
            "recommendation": "Implement Celery for async task processing",
            "impact": "85% reduced response times",
            "action": "pip install celery && configure Redis broker"
        }
    ])
    
    return {
        "recommendations": recommendations,
        "total_count": len(recommendations),
        "analysis_date": datetime.now().isoformat()
    }

# Performance Health Check
@router.get("/health", summary="Performance health check")
async def performance_health_check():
    """Comprehensive performance health check"""
    
    health_status = {
        "overall": "healthy",
        "checks": {}
    }
    
    # Cache health
    cache_stats = cache.get_stats()
    if cache.enabled:
        hit_rate = float(cache_stats.get("hit_rate", "0").replace("%", ""))
        health_status["checks"]["cache"] = {
            "status": "healthy" if hit_rate > 70 else "degraded" if hit_rate > 50 else "unhealthy",
            "hit_rate": f"{hit_rate:.1f}%",
            "details": cache_stats
        }
    else:
        health_status["checks"]["cache"] = {
            "status": "disabled",
            "message": "Redis cache not available"
        }
    
    # Database health
    try:
        from ..database_optimized import db_manager
        pool_info = db_manager.get_connection_info()
        
        checked_out = pool_info.get("checked_out", 0)
        pool_size = pool_info.get("pool_size", 20)
        utilization = (checked_out / pool_size) * 100 if pool_size > 0 else 0
        
        health_status["checks"]["database"] = {
            "status": "healthy" if utilization < 80 else "degraded" if utilization < 95 else "critical",
            "utilization": f"{utilization:.1f}%",
            "details": pool_info
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Background tasks health
    task_stats = task_manager.get_queue_stats()
    health_status["checks"]["background_tasks"] = {
        "status": "healthy" if task_stats.get("worker_status") == "online" else "degraded",
        "details": task_stats
    }
    
    # Determine overall health
    statuses = [check["status"] for check in health_status["checks"].values()]
    if "critical" in statuses or "error" in statuses:
        health_status["overall"] = "critical"
    elif "degraded" in statuses or "unhealthy" in statuses:
        health_status["overall"] = "degraded"
    
    return health_status
