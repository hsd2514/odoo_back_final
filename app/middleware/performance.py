"""
Performance middleware for FastAPI application.
Includes caching, compression, rate limiting, and monitoring.
"""

from __future__ import annotations

import time
import gzip
import json
from typing import Callable, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
import asyncio

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Simple in-memory cache (for production, use Redis)
class SimpleCache:
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self.cache = {}
        self.ttl = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[any]:
        if key in self.cache:
            if datetime.now() < self.ttl[key]:
                return self.cache[key]
            else:
                # Expired
                del self.cache[key]
                del self.ttl[key]
        return None
    
    def set(self, key: str, value: any, ttl: Optional[int] = None) -> None:
        self.cache[key] = value
        expires_at = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
        self.ttl[key] = expires_at
    
    def delete(self, key: str) -> None:
        self.cache.pop(key, None)
        self.ttl.pop(key, None)
    
    def clear(self) -> None:
        self.cache.clear()
        self.ttl.clear()
    
    def stats(self) -> dict:
        return {
            "total_keys": len(self.cache),
            "expired_keys": sum(1 for exp_time in self.ttl.values() if datetime.now() >= exp_time)
        }

# Global cache instance
cache = SimpleCache()

class CompressionMiddleware(BaseHTTPMiddleware):
    """Middleware to compress responses."""
    
    def __init__(self, app: FastAPI, minimum_size: int = 1000):
        super().__init__(app)
        self.minimum_size = minimum_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Check if compression is needed
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding:
            return response
        
        # Get response content
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        
        # Compress if size is above threshold
        if len(response_body) >= self.minimum_size:
            compressed_body = gzip.compress(response_body)
            response.headers["content-encoding"] = "gzip"
            response.headers["content-length"] = str(len(compressed_body))
            
            return Response(
                content=compressed_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""
    
    def __init__(self, app: FastAPI, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls  # Number of calls allowed
        self.period = period  # Time period in seconds
        self.clients = defaultdict(lambda: deque())
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)
        now = time.time()
        
        # Clean old entries
        client_calls = self.clients[client_ip]
        while client_calls and client_calls[0] <= now - self.period:
            client_calls.popleft()
        
        # Check rate limit
        if len(client_calls) >= self.calls:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"}
            )
        
        # Add current request
        client_calls.append(now)
        
        response = await call_next(request)
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor and log performance metrics."""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.request_times = deque(maxlen=1000)  # Keep last 1000 requests
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        self.request_times.append(process_time)
        
        # Add performance headers
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log slow requests (> 1 second)
        if process_time > 1.0:
            print(f"Slow request: {request.method} {request.url.path} took {process_time:.2f}s")
        
        return response
    
    def get_stats(self) -> dict:
        if not self.request_times:
            return {"avg_response_time": 0, "total_requests": 0}
        
        return {
            "avg_response_time": sum(self.request_times) / len(self.request_times),
            "total_requests": len(self.request_times),
            "min_response_time": min(self.request_times),
            "max_response_time": max(self.request_times)
        }

class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware to cache GET requests."""
    
    def __init__(self, app: FastAPI, cache_ttl: int = 300):
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.cacheable_paths = {
            "/catalog/categories",
            "/catalog/products", 
            "/roles",
            "/engage/promotions"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only cache GET requests for specific paths
        if request.method != "GET" or not self._is_cacheable(request.url.path):
            return await call_next(request)
        
        # Generate cache key
        cache_key = f"{request.method}:{request.url.path}:{request.url.query}"
        
        # Try to get from cache
        cached_response = cache.get(cache_key)
        if cached_response:
            return JSONResponse(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers={"X-Cache": "HIT"}
            )
        
        # Get response and cache it
        response = await call_next(request)
        
        if response.status_code == 200:
            # Read response content
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            try:
                content = json.loads(response_body.decode())
                cache.set(cache_key, {
                    "content": content,
                    "status_code": response.status_code
                }, self.cache_ttl)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass  # Don't cache if can't parse JSON
            
            # Return new response with cache header
            return JSONResponse(
                content=content if 'content' in locals() else response_body.decode(),
                status_code=response.status_code,
                headers={"X-Cache": "MISS"}
            )
        
        return response
    
    def _is_cacheable(self, path: str) -> bool:
        return any(cacheable_path in path for cacheable_path in self.cacheable_paths)

# Global middleware instances for stats
performance_middleware = PerformanceMiddleware(None)

def add_performance_middleware(app: FastAPI) -> None:
    """Add all performance middleware to the FastAPI app."""
    
    # Add middleware in reverse order (last added = first executed)
    app.add_middleware(PerformanceMiddleware)
    app.add_middleware(CacheMiddleware, cache_ttl=300)  # 5 minutes cache
    app.add_middleware(RateLimitMiddleware, calls=100, period=60)  # 100 calls per minute
    app.add_middleware(CompressionMiddleware, minimum_size=1000)
    
    print("✅ Performance middleware added successfully")

def get_performance_stats() -> dict:
    """Get current performance statistics."""
    return {
        "cache_stats": cache.stats(),
        "performance_stats": performance_middleware.get_stats(),
        "timestamp": datetime.now().isoformat()
    }
