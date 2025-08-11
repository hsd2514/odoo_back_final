"""
Response Compression and API Optimization Middleware
Provides gzip compression and response optimization for peak performance
"""
from __future__ import annotations

import gzip
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import time

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp

from ..utils.redis_cache import cache, RateLimiter

logger = logging.getLogger(__name__)

class CompressionMiddleware(BaseHTTPMiddleware):
    """Gzip compression middleware for API responses"""
    
    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        compression_level: int = 6
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return response
        
        # Skip compression for small responses
        if hasattr(response, 'body'):
            body = response.body
            if len(body) < self.minimum_size:
                return response
            
            # Compress response
            compressed_body = gzip.compress(body, compresslevel=self.compression_level)
            
            # Update response
            response.body = compressed_body
            response.headers["content-encoding"] = "gzip"
            response.headers["content-length"] = str(len(compressed_body))
            response.headers["vary"] = "Accept-Encoding"
        
        return response

class ResponseOptimizationMiddleware(BaseHTTPMiddleware):
    """Response optimization and caching middleware"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.cacheable_endpoints = {
            "/catalog/products": 600,  # 10 minutes
            "/catalog/categories": 3600,  # 1 hour
            "/engage/promotions": 1800,  # 30 minutes
        }
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Check if endpoint is cacheable
        endpoint = str(request.url.path)
        cache_ttl = self.cacheable_endpoints.get(endpoint)
        
        if cache_ttl and request.method == "GET":
            # Generate cache key from URL and query params
            cache_key = f"response:{endpoint}:{str(request.query_params)}"
            
            # Try to get cached response
            cached_response = cache.get(cache_key)
            if cached_response:
                # Return cached response with cache headers
                return JSONResponse(
                    content=cached_response,
                    headers={
                        "X-Cache": "HIT",
                        "Cache-Control": f"public, max-age={cache_ttl}",
                        "X-Response-Time": f"{(time.time() - start_time) * 1000:.2f}ms"
                    }
                )
        
        # Process request
        response = await call_next(request)
        processing_time = (time.time() - start_time) * 1000
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{processing_time:.2f}ms"
        
        # Cache successful GET responses
        if (cache_ttl and request.method == "GET" and 
            response.status_code == 200 and 
            hasattr(response, 'body')):
            
            try:
                # Parse and cache response body
                body_str = response.body.decode() if isinstance(response.body, bytes) else str(response.body)
                response_data = json.loads(body_str)
                
                cache.set(cache_key, response_data, cache_ttl)
                response.headers["X-Cache"] = "MISS"
                response.headers["Cache-Control"] = f"public, max-age={cache_ttl}"
                
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    def __init__(
        self,
        app: ASGIApp,
        calls_per_minute: int = 100,
        burst_limit: int = 150
    ):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.burst_limit = burst_limit
        self.rate_limiter = RateLimiter()
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "unknown")
        identifier = f"{client_ip}:{hash(user_agent)}"
        
        # Check rate limit
        if not self.rate_limiter.check_rate_limit(
            identifier,
            limit=self.calls_per_minute,
            window=60  # 1 minute window
        ):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "limit": self.calls_per_minute,
                    "window": "1 minute",
                    "retry_after": 60
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.calls_per_minute),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'"
        })
        
        return response

class APIMetricsMiddleware(BaseHTTPMiddleware):
    """API metrics collection middleware"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.metrics = {
            "total_requests": 0,
            "total_errors": 0,
            "average_response_time": 0,
            "endpoint_stats": {},
            "status_code_stats": {}
        }
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            logger.error(f"Request failed: {e}")
            status_code = 500
            response = JSONResponse(
                status_code=500,
                content={"error": "Internal server error"}
            )
        
        # Calculate metrics
        processing_time = (time.time() - start_time) * 1000
        endpoint = f"{request.method} {request.url.path}"
        
        # Update metrics
        self.metrics["total_requests"] += 1
        if status_code >= 400:
            self.metrics["total_errors"] += 1
        
        # Update average response time
        current_avg = self.metrics["average_response_time"]
        total_requests = self.metrics["total_requests"]
        self.metrics["average_response_time"] = (
            (current_avg * (total_requests - 1) + processing_time) / total_requests
        )
        
        # Update endpoint stats
        if endpoint not in self.metrics["endpoint_stats"]:
            self.metrics["endpoint_stats"][endpoint] = {
                "count": 0,
                "avg_time": 0,
                "errors": 0
            }
        
        endpoint_stats = self.metrics["endpoint_stats"][endpoint]
        endpoint_stats["count"] += 1
        endpoint_stats["avg_time"] = (
            (endpoint_stats["avg_time"] * (endpoint_stats["count"] - 1) + processing_time) /
            endpoint_stats["count"]
        )
        if status_code >= 400:
            endpoint_stats["errors"] += 1
        
        # Update status code stats
        status_range = f"{status_code // 100}xx"
        self.metrics["status_code_stats"][status_range] = (
            self.metrics["status_code_stats"].get(status_range, 0) + 1
        )
        
        # Add metrics to response headers
        response.headers["X-Request-ID"] = str(id(request))
        response.headers["X-Processing-Time"] = f"{processing_time:.2f}ms"
        
        return response
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics"""
        error_rate = (
            self.metrics["total_errors"] / self.metrics["total_requests"] * 100
            if self.metrics["total_requests"] > 0 else 0
        )
        
        # Get top 10 slowest endpoints
        slowest_endpoints = sorted(
            [
                {
                    "endpoint": endpoint,
                    "avg_time": stats["avg_time"],
                    "count": stats["count"],
                    "error_rate": stats["errors"] / stats["count"] * 100 if stats["count"] > 0 else 0
                }
                for endpoint, stats in self.metrics["endpoint_stats"].items()
            ],
            key=lambda x: x["avg_time"],
            reverse=True
        )[:10]
        
        return {
            **self.metrics,
            "error_rate": f"{error_rate:.2f}%",
            "slowest_endpoints": slowest_endpoints,
            "uptime": datetime.now().isoformat()
        }

# Global metrics instance
api_metrics = APIMetricsMiddleware

class ResponseFormatter:
    """Standardized API response formatting"""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format successful response"""
        response = {
            "success": True,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if data is not None:
            response["data"] = data
        
        if meta:
            response["meta"] = meta
        
        return response
    
    @staticmethod
    def error(
        error: str,
        details: Optional[Any] = None,
        code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Format error response"""
        response = {
            "success": False,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        if details:
            response["details"] = details
        
        if code:
            response["error_code"] = code
        
        return response
    
    @staticmethod
    def paginated(
        data: List[Any],
        page: int,
        per_page: int,
        total: int,
        message: str = "Success"
    ) -> Dict[str, Any]:
        """Format paginated response"""
        total_pages = (total + per_page - 1) // per_page
        
        return ResponseFormatter.success(
            data=data,
            message=message,
            meta={
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        )

# Export middleware components
__all__ = [
    'CompressionMiddleware',
    'ResponseOptimizationMiddleware', 
    'RateLimitMiddleware',
    'SecurityHeadersMiddleware',
    'APIMetricsMiddleware',
    'ResponseFormatter'
]
