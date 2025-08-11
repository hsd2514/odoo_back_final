"""
Monitoring and health check utilities for performance tracking.
"""

from __future__ import annotations

import psutil
import time
from typing import Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, asdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database_optimized import get_db, db_manager
from ..middleware.performance import get_performance_stats
from ..utils.auth import require_roles

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

@dataclass
class SystemMetrics:
    """System performance metrics."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    uptime_seconds: float
    timestamp: str

@dataclass
class DatabaseMetrics:
    """Database performance metrics."""
    connection_pool_size: Any
    connections_checked_in: Any
    connections_checked_out: Any
    connection_overflow: Any
    timestamp: str

@dataclass
class ApplicationMetrics:
    """Application performance metrics."""
    total_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    cache_hit_ratio: float
    cache_total_keys: int
    timestamp: str

class PerformanceMonitor:
    """Main performance monitoring class."""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics_history: List[Dict[str, Any]] = []
        self.max_history = 1000  # Keep last 1000 metrics
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return SystemMetrics(
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_percent=memory.percent,
            memory_used_mb=memory.used / 1024 / 1024,
            memory_total_mb=memory.total / 1024 / 1024,
            disk_usage_percent=disk.percent,
            disk_free_gb=disk.free / 1024 / 1024 / 1024,
            uptime_seconds=time.time() - self.start_time,
            timestamp=datetime.now().isoformat()
        )
    
    def get_database_metrics(self) -> DatabaseMetrics:
        """Get current database metrics."""
        db_info = db_manager.get_connection_info()
        
        return DatabaseMetrics(
            connection_pool_size=db_info.get("pool_size", "N/A"),
            connections_checked_in=db_info.get("checked_in", "N/A"),
            connections_checked_out=db_info.get("checked_out", "N/A"),
            connection_overflow=db_info.get("overflow", "N/A"),
            timestamp=datetime.now().isoformat()
        )
    
    def get_application_metrics(self) -> ApplicationMetrics:
        """Get current application metrics."""
        perf_stats = get_performance_stats()
        
        # Calculate cache hit ratio
        cache_stats = perf_stats.get("cache_stats", {})
        total_keys = cache_stats.get("total_keys", 0)
        expired_keys = cache_stats.get("expired_keys", 0)
        hit_ratio = ((total_keys - expired_keys) / total_keys * 100) if total_keys > 0 else 0
        
        performance_stats = perf_stats.get("performance_stats", {})
        
        return ApplicationMetrics(
            total_requests=performance_stats.get("total_requests", 0),
            avg_response_time=performance_stats.get("avg_response_time", 0),
            min_response_time=performance_stats.get("min_response_time", 0),
            max_response_time=performance_stats.get("max_response_time", 0),
            cache_hit_ratio=hit_ratio,
            cache_total_keys=total_keys,
            timestamp=datetime.now().isoformat()
        )
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get all metrics in one call."""
        return {
            "system": asdict(self.get_system_metrics()),
            "database": asdict(self.get_database_metrics()),
            "application": asdict(self.get_application_metrics())
        }
    
    def record_metrics(self):
        """Record current metrics to history."""
        metrics = self.get_comprehensive_metrics()
        self.metrics_history.append(metrics)
        
        # Keep only last N metrics
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history:]
    
    def get_metrics_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get metrics history."""
        return self.metrics_history[-limit:]
    
    def get_performance_alerts(self) -> List[Dict[str, str]]:
        """Get performance alerts based on thresholds."""
        alerts = []
        
        try:
            system = self.get_system_metrics()
            app = self.get_application_metrics()
            
            # CPU alert
            if system.cpu_percent > 80:
                alerts.append({
                    "type": "warning",
                    "message": f"High CPU usage: {system.cpu_percent:.1f}%",
                    "timestamp": system.timestamp
                })
            
            # Memory alert
            if system.memory_percent > 85:
                alerts.append({
                    "type": "warning", 
                    "message": f"High memory usage: {system.memory_percent:.1f}%",
                    "timestamp": system.timestamp
                })
            
            # Disk alert
            if system.disk_usage_percent > 90:
                alerts.append({
                    "type": "error",
                    "message": f"Low disk space: {system.disk_usage_percent:.1f}% used",
                    "timestamp": system.timestamp
                })
            
            # Response time alert
            if app.avg_response_time > 2.0:
                alerts.append({
                    "type": "warning",
                    "message": f"Slow response time: {app.avg_response_time:.2f}s",
                    "timestamp": app.timestamp
                })
            
        except Exception as e:
            alerts.append({
                "type": "error",
                "message": f"Monitoring error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
        
        return alerts

# Global monitor instance
monitor = PerformanceMonitor()

class HealthChecker:
    """Application health check utilities."""
    
    @staticmethod
    def check_database_health(db: Session) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            start_time = time.time()
            db.execute("SELECT 1")
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": response_time * 1000,
                "connection_info": db_manager.get_connection_info()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": None
            }
    
    @staticmethod
    def check_stripe_integration() -> Dict[str, Any]:
        """Check Stripe integration health."""
        try:
            from ..services.stripe_service import stripe_service
            
            # Simple configuration check
            if stripe_service.stripe.api_key:
                return {"status": "configured", "message": "Stripe API key configured"}
            else:
                return {"status": "not_configured", "message": "Stripe API key not configured"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    @staticmethod
    def check_email_service() -> Dict[str, Any]:
        """Check email service health."""
        try:
            from ..config import get_settings
            settings = get_settings()
            
            if settings.smtp_username and settings.smtp_password:
                return {"status": "configured", "message": "Email service configured"}
            else:
                return {"status": "not_configured", "message": "Email service not configured"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

health_checker = HealthChecker()

# API Endpoints

@router.get("/health", summary="Application health check")
def health_check(db: Session = Depends(get_db)):
    """Get application health status."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": time.time() - monitor.start_time,
        "database": health_checker.check_database_health(db),
        "stripe": health_checker.check_stripe_integration(),
        "email": health_checker.check_email_service()
    }

@router.get("/metrics", summary="Get performance metrics")
def get_metrics(_: None = Depends(require_roles("Admin"))):
    """Get current performance metrics (Admin only)."""
    return monitor.get_comprehensive_metrics()

@router.get("/metrics/history", summary="Get metrics history")
def get_metrics_history(
    limit: int = 100,
    _: None = Depends(require_roles("Admin"))
):
    """Get performance metrics history (Admin only)."""
    return {
        "metrics": monitor.get_metrics_history(limit),
        "total_recorded": len(monitor.metrics_history)
    }

@router.get("/alerts", summary="Get performance alerts")
def get_alerts(_: None = Depends(require_roles("Admin"))):
    """Get current performance alerts (Admin only)."""
    return {
        "alerts": monitor.get_performance_alerts(),
        "timestamp": datetime.now().isoformat()
    }

@router.get("/system", summary="Get system information")
def get_system_info(_: None = Depends(require_roles("Admin"))):
    """Get detailed system information (Admin only)."""
    return {
        "system": asdict(monitor.get_system_metrics()),
        "python_version": f"{psutil.PYTHON_VERSION[0]}.{psutil.PYTHON_VERSION[1]}.{psutil.PYTHON_VERSION[2]}",
        "platform": psutil.platform_module.platform(),
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
    }

@router.post("/cache/clear", summary="Clear application cache")
def clear_cache(_: None = Depends(require_roles("Admin"))):
    """Clear application cache (Admin only)."""
    from ..middleware.performance import cache
    cache.clear()
    return {"message": "Cache cleared successfully"}

@router.post("/metrics/record", summary="Record current metrics")
def record_metrics(_: None = Depends(require_roles("Admin"))):
    """Manually record current metrics (Admin only)."""
    monitor.record_metrics()
    return {"message": "Metrics recorded successfully"}
