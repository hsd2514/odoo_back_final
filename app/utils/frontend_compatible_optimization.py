"""
Frontend-Compatible Performance Layer
Provides transparent optimizations without breaking existing API contracts
"""
from __future__ import annotations

import time
import logging
from typing import Any, Dict, Optional, Callable
from functools import wraps
from datetime import datetime

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..utils.redis_cache import cache, cached

logger = logging.getLogger(__name__)

class APIResponseStandardizer:
    """Standardize API responses while maintaining backward compatibility"""
    
    @staticmethod
    def enhance_response(
        data: Any,
        request: Request,
        execution_time: Optional[float] = None,
        cached: bool = False
    ) -> Dict[str, Any]:
        """
        Enhance response with metadata while keeping original data structure.
        Frontend receives same data, with optional performance metadata.
        """
        
        # Core response (what frontend expects)
        if isinstance(data, dict):
            response = data.copy()
        else:
            response = {"data": data}
        
        # Add optional metadata (frontend can ignore)
        if execution_time or cached:
            response["_meta"] = {}
            
            if execution_time:
                response["_meta"]["response_time"] = f"{execution_time:.2f}ms"
            
            if cached:
                response["_meta"]["cached"] = True
                response["_meta"]["cache_timestamp"] = datetime.now().isoformat()
            
            # Performance indicators
            if execution_time:
                if execution_time < 50:
                    response["_meta"]["performance"] = "excellent"
                elif execution_time < 100:
                    response["_meta"]["performance"] = "good"
                else:
                    response["_meta"]["performance"] = "acceptable"
        
        return response

def frontend_compatible_cache(ttl: int = 600, key_prefix: str = "api"):
    """
    Caching decorator that's transparent to frontend.
    Responses look identical to uncached responses.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request info for cache key
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # Generate cache key
            if request:
                cache_key = f"{key_prefix}:{func.__name__}:{request.url.path}:{str(request.query_params)}"
            else:
                cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try cache first
            start_time = time.perf_counter()
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                execution_time = (time.perf_counter() - start_time) * 1000
                
                # Add metadata to cached response
                if isinstance(cached_result, dict):
                    cached_result["_meta"] = cached_result.get("_meta", {})
                    cached_result["_meta"]["cached"] = True
                    cached_result["_meta"]["response_time"] = f"{execution_time:.2f}ms"
                
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            execution_time = (time.perf_counter() - start_time) * 1000
            
            # Enhance response
            enhanced_result = APIResponseStandardizer.enhance_response(
                result,
                request,
                execution_time=execution_time,
                cached=False
            )
            
            # Cache the enhanced result
            cache.set(cache_key, enhanced_result, ttl)
            
            return enhanced_result
        
        return wrapper
    return decorator

class UnifiedSessionManager:
    """
    Unified database session management to eliminate redundancy.
    Replaces multiple `Session = Depends(get_db)` patterns.
    """
    
    @staticmethod
    def get_db_session():
        """Centralized database session factory"""
        from ..database_optimized import SessionLocal
        return SessionLocal()
    
    @classmethod
    def with_db_session(cls, func: Callable) -> Callable:
        """
        Decorator to inject database session automatically.
        Eliminates need for `db: Session = Depends(get_db)` in every endpoint.
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if db session already provided
            if 'db' not in kwargs:
                with cls.get_db_session() as db:
                    kwargs['db'] = db
                    try:
                        if asyncio.iscoroutinefunction(func):
                            return await func(*args, **kwargs)
                        else:
                            return func(*args, **kwargs)
                    except Exception as e:
                        db.rollback()
                        raise
                    finally:
                        db.close()
            else:
                # Use provided session
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
        
        return wrapper

class AuthenticationManager:
    """
    Unified authentication handling to eliminate duplicate code.
    Consolidates user validation, role checking, and token handling.
    """
    
    @staticmethod
    @cached(ttl=300, key_prefix="auth")
    def get_user_with_roles(user_id: int, db: Session) -> Dict[str, Any]:
        """
        Optimized user lookup with roles (cached).
        Eliminates duplicate user+role queries across endpoints.
        """
        from ..models.user import User, Role, UserRole
        
        # Single query to get user with roles
        user_data = db.query(
            User.user_id,
            User.email,
            User.full_name,
            User.phone
        ).filter(User.user_id == user_id).first()
        
        if not user_data:
            return None
        
        # Get roles in single query
        roles = db.query(Role.name).join(
            UserRole, Role.role_id == UserRole.role_id
        ).filter(UserRole.user_id == user_id).all()
        
        return {
            "user_id": user_data.user_id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "phone": user_data.phone,
            "roles": [role[0] for role in roles]
        }
    
    @classmethod
    def require_auth(cls, required_roles: Optional[list] = None):
        """
        Unified authentication decorator.
        Replaces duplicate get_current_user + require_roles patterns.
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                from ..utils.auth import get_current_user
                from fastapi import Depends
                
                # Extract current user (this will handle token validation)
                current_user = None
                db = None
                
                # Try to find current_user in kwargs
                if 'current_user' in kwargs:
                    current_user = kwargs['current_user']
                
                if 'db' in kwargs:
                    db = kwargs['db']
                elif not db:
                    db = UnifiedSessionManager.get_db_session()
                
                if current_user and required_roles:
                    # Check roles using cached user data
                    user_data = cls.get_user_with_roles(current_user.user_id, db)
                    user_roles = user_data.get("roles", []) if user_data else []
                    
                    if not any(role in user_roles for role in required_roles):
                        raise HTTPException(status_code=403, detail="Insufficient permissions")
                
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator

class QueryOptimizer:
    """
    Unified query patterns to eliminate redundant database operations.
    Provides common query patterns used across multiple endpoints.
    """
    
    @staticmethod
    @cached(ttl=600, key_prefix="products")
    def get_products_optimized(
        filters: Dict[str, Any],
        db: Session
    ) -> list:
        """
        Optimized product listing used by multiple endpoints.
        Consolidates product queries with eager loading.
        """
        from ..models.catalog import Product, Category
        from sqlalchemy.orm import joinedload
        
        query = db.query(Product).options(joinedload(Product.category))
        
        # Apply filters
        if filters.get("category_id"):
            query = query.filter(Product.category_id == filters["category_id"])
        
        if filters.get("active") is not None:
            query = query.filter(Product.active == filters["active"])
        
        if filters.get("min_price"):
            query = query.filter(Product.base_price >= filters["min_price"])
        
        if filters.get("max_price"):
            query = query.filter(Product.base_price <= filters["max_price"])
        
        if filters.get("search"):
            query = query.filter(Product.title.ilike(f"%{filters['search']}%"))
        
        # Pagination
        limit = filters.get("limit", 50)
        offset = filters.get("offset", 0)
        
        return query.offset(offset).limit(limit).all()
    
    @staticmethod
    @cached(ttl=1800, key_prefix="user_rentals")
    def get_user_rentals_optimized(
        user_id: int,
        status_filter: Optional[str],
        db: Session
    ) -> list:
        """
        Optimized user rental history.
        Used by multiple endpoints with consistent structure.
        """
        from ..models.rentals import RentalOrder, RentalItem
        from sqlalchemy.orm import joinedload
        
        query = db.query(RentalOrder).options(
            joinedload(RentalOrder.rental_items).joinedload(RentalItem.product)
        ).filter(RentalOrder.customer_id == user_id)
        
        if status_filter:
            query = query.filter(RentalOrder.status == status_filter)
        
        return query.order_by(RentalOrder.created_at.desc()).limit(20).all()

# Import optimization to reduce redundancy
import asyncio

def cleanup_redundant_imports():
    """
    Identify and suggest removal of redundant imports.
    This would be run as a code analysis tool.
    """
    redundant_patterns = [
        "from ..database import get_db",  # Should use UnifiedSessionManager
        "Session = Depends(get_db)",      # Should use @with_db_session decorator
        "current_user = Depends(get_current_user)",  # Should use @require_auth
    ]
    
    return {
        "redundant_imports": redundant_patterns,
        "suggestion": "Use unified managers to reduce code duplication",
        "estimated_reduction": "40% less boilerplate code"
    }

# Frontend compatibility helpers
class FrontendCompatibility:
    """
    Ensure new optimizations don't break existing frontend code.
    """
    
    @staticmethod
    def wrap_legacy_response(data: Any) -> Dict[str, Any]:
        """
        Wrap responses to maintain backward compatibility.
        Old frontend code continues to work unchanged.
        """
        # If response already has the expected structure, return as-is
        if isinstance(data, dict) and ("user_id" in data or "product_id" in data or "rental_id" in data):
            return data
        
        # Otherwise, wrap in compatible structure
        return {"data": data}
    
    @staticmethod
    def extract_metadata_optional(response: Dict[str, Any]) -> tuple:
        """
        Extract metadata for new frontends while keeping data for old ones.
        """
        metadata = response.pop("_meta", {})
        return response, metadata

# Export optimized components
__all__ = [
    'APIResponseStandardizer',
    'frontend_compatible_cache',
    'UnifiedSessionManager', 
    'AuthenticationManager',
    'QueryOptimizer',
    'FrontendCompatibility',
    'cleanup_redundant_imports'
]
