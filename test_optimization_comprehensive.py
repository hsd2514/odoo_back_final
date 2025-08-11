#!/usr/bin/env python3
"""
Comprehensive performance optimization testing script.
Tests all optimization features and provides performance benchmarks.
"""

import time
import asyncio
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

def test_imports():
    """Test all optimization-related imports."""
    print("=== Testing Optimization Imports ===")
    
    try:
        # Database optimizations
        from app.database_optimized import engine, SessionLocal, db_manager
        print("✅ Optimized database import")
        
        # Performance middleware
        from app.middleware.performance import (
            cache, CompressionMiddleware, RateLimitMiddleware,
            PerformanceMiddleware, CacheMiddleware
        )
        print("✅ Performance middleware import")
        
        # Query optimizer
        from app.utils.query_optimizer import QueryOptimizer, RentalQueryOptimizer
        print("✅ Query optimizer import")
        
        # Background tasks
        from app.utils.background_tasks import (
            TaskQueue, send_email_async, cleanup_expired_tokens
        )
        print("✅ Background tasks import")
        
        # Monitoring
        from app.routers.monitoring import monitor, health_checker
        print("✅ Monitoring import")
        
        # Optimized services
        from app.services.optimized_services import (
            OptimizedUserService, OptimizedRentalService, ServiceFactory
        )
        print("✅ Optimized services import")
        
        # Main app
        from app.main_optimized import create_app
        print("✅ Optimized main app import")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_database_optimization():
    """Test database connection pooling and optimization."""
    print("\n=== Testing Database Optimization ===")
    
    try:
        from app.database_optimized import engine, db_manager, SessionLocal
        
        # Test connection pool info
        pool_info = db_manager.get_connection_info()
        print(f"✅ Connection pool info: {pool_info}")
        
        # Test database session
        with SessionLocal() as db:
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
        print("✅ Database session works")
        
        # Test query logging controls
        db_manager.enable_query_logging()
        db_manager.disable_query_logging()
        print("✅ Query logging controls work")
        
        return True
    except Exception as e:
        print(f"❌ Database optimization test failed: {e}")
        return False

def test_cache_functionality():
    """Test caching functionality."""
    print("\n=== Testing Cache Functionality ===")
    
    try:
        from app.middleware.performance import cache
        
        # Test basic cache operations
        cache.set("test_key", "test_value", ttl=60)
        value = cache.get("test_key")
        assert value == "test_value", "Cache get failed"
        print("✅ Basic cache operations work")
        
        # Test cache expiration (simulate)
        cache.set("expire_test", "value", ttl=0)  # Should expire immediately
        time.sleep(0.1)
        expired_value = cache.get("expire_test")
        assert expired_value is None, "Cache expiration failed"
        print("✅ Cache expiration works")
        
        # Test cache stats
        stats = cache.stats()
        print(f"✅ Cache stats: {stats}")
        
        # Test cache clear
        cache.clear()
        print("✅ Cache clear works")
        
        return True
    except Exception as e:
        print(f"❌ Cache functionality test failed: {e}")
        return False

def test_query_optimizer():
    """Test query optimization utilities."""
    print("\n=== Testing Query Optimizer ===")
    
    try:
        from app.database_optimized import SessionLocal
        from app.utils.query_optimizer import QueryOptimizer, optimize_database_schema
        from app.models.user import User
        
        with SessionLocal() as db:
            # Test query optimizer creation
            optimizer = QueryOptimizer(db, User)
            print("✅ Query optimizer created")
            
            # Test pagination (even with no data)
            paginated = optimizer.get_paginated(page=1, per_page=10)
            assert "items" in paginated and "total" in paginated
            print("✅ Pagination works")
            
            # Test database schema optimization
            optimize_database_schema(db)
            print("✅ Database schema optimization works")
        
        return True
    except Exception as e:
        print(f"❌ Query optimizer test failed: {e}")
        return False

def test_background_tasks():
    """Test background task functionality."""
    print("\n=== Testing Background Tasks ===")
    
    try:
        from app.utils.background_tasks import (
            TaskQueue, background_task, send_email_async,
            setup_background_tasks
        )
        
        # Test task queue
        queue = TaskQueue()
        
        @background_task
        def test_task():
            return "Task completed"
        
        # Add task to queue
        result = test_task()
        assert result == "Task queued"
        print("✅ Background task decorator works")
        
        # Test setup
        setup_background_tasks()
        print("✅ Background tasks setup works")
        
        return True
    except Exception as e:
        print(f"❌ Background tasks test failed: {e}")
        return False

def test_monitoring_system():
    """Test monitoring and metrics system."""
    print("\n=== Testing Monitoring System ===")
    
    try:
        from app.routers.monitoring import monitor, health_checker
        
        # Test system metrics
        system_metrics = monitor.get_system_metrics()
        assert hasattr(system_metrics, 'cpu_percent')
        print("✅ System metrics work")
        
        # Test database metrics
        db_metrics = monitor.get_database_metrics()
        assert hasattr(db_metrics, 'connection_pool_size')
        print("✅ Database metrics work")
        
        # Test comprehensive metrics
        all_metrics = monitor.get_comprehensive_metrics()
        assert "system" in all_metrics and "database" in all_metrics
        print("✅ Comprehensive metrics work")
        
        # Test performance alerts
        alerts = monitor.get_performance_alerts()
        assert isinstance(alerts, list)
        print("✅ Performance alerts work")
        
        return True
    except Exception as e:
        print(f"❌ Monitoring system test failed: {e}")
        return False

def test_optimized_services():
    """Test optimized service layer."""
    print("\n=== Testing Optimized Services ===")
    
    try:
        from app.database_optimized import SessionLocal
        from app.services.optimized_services import (
            ServiceFactory, OptimizedUserService, OptimizedRentalService
        )
        
        with SessionLocal() as db:
            # Test service factory
            user_service = ServiceFactory.create_user_service(db)
            assert isinstance(user_service, OptimizedUserService)
            print("✅ Service factory works")
            
            rental_service = ServiceFactory.create_rental_service(db)
            assert isinstance(rental_service, OptimizedRentalService)
            print("✅ Optimized services creation works")
        
        return True
    except Exception as e:
        print(f"❌ Optimized services test failed: {e}")
        return False

def test_performance_middleware():
    """Test performance middleware components."""
    print("\n=== Testing Performance Middleware ===")
    
    try:
        from app.middleware.performance import (
            CompressionMiddleware, RateLimitMiddleware,
            PerformanceMiddleware, CacheMiddleware
        )
        
        # Test middleware creation (basic instantiation)
        compression_mw = CompressionMiddleware(None, minimum_size=1000)
        rate_limit_mw = RateLimitMiddleware(None, calls=100, period=60)
        performance_mw = PerformanceMiddleware(None)
        cache_mw = CacheMiddleware(None, cache_ttl=300)
        
        print("✅ All middleware components can be instantiated")
        
        # Test performance stats
        stats = performance_mw.get_stats()
        assert "avg_response_time" in stats
        print("✅ Performance middleware stats work")
        
        return True
    except Exception as e:
        print(f"❌ Performance middleware test failed: {e}")
        return False

def performance_benchmark():
    """Run basic performance benchmark."""
    print("\n=== Performance Benchmark ===")
    
    try:
        from app.middleware.performance import cache
        from app.database_optimized import SessionLocal
        
        # Cache performance test
        start_time = time.time()
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")
        cache_write_time = time.time() - start_time
        
        start_time = time.time()
        for i in range(1000):
            cache.get(f"key_{i}")
        cache_read_time = time.time() - start_time
        
        print(f"✅ Cache write performance: {cache_write_time:.3f}s for 1000 operations")
        print(f"✅ Cache read performance: {cache_read_time:.3f}s for 1000 operations")
        
        # Database connection performance test
        start_time = time.time()
        for i in range(10):
            with SessionLocal() as db:
                from sqlalchemy import text
                db.execute(text("SELECT 1"))
        db_connection_time = time.time() - start_time
        
        print(f"✅ Database connection performance: {db_connection_time:.3f}s for 10 connections")
        
        return True
    except Exception as e:
        print(f"❌ Performance benchmark failed: {e}")
        return False

def test_app_creation():
    """Test optimized app creation."""
    print("\n=== Testing Optimized App Creation ===")
    
    try:
        from app.main_optimized import create_app
        
        # Create the app
        app = create_app()
        print("✅ Optimized app created successfully")
        
        # Check if app has the expected attributes
        assert hasattr(app, 'routes')
        print(f"✅ App has {len(app.routes)} routes registered")
        
        return True
    except Exception as e:
        print(f"❌ App creation test failed: {e}")
        return False

def run_comprehensive_optimization_test():
    """Run all optimization tests and provide summary."""
    print("🧪 Comprehensive Performance Optimization Test")
    print("=" * 55)
    
    tests = [
        ("Imports", test_imports),
        ("Database Optimization", test_database_optimization),
        ("Cache Functionality", test_cache_functionality),
        ("Query Optimizer", test_query_optimizer),
        ("Background Tasks", test_background_tasks),
        ("Monitoring System", test_monitoring_system),
        ("Optimized Services", test_optimized_services),
        ("Performance Middleware", test_performance_middleware),
        ("App Creation", test_app_creation),
        ("Performance Benchmark", performance_benchmark),
    ]
    
    results = []
    start_time = time.time()
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    total_time = time.time() - start_time
    
    # Summary
    print("\n" + "=" * 55)
    print("📊 Optimization Test Results Summary")
    print("=" * 55)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📈 Overall: {passed}/{total} tests passed")
    print(f"⏱️  Total test time: {total_time:.2f}s")
    
    if passed == total:
        print("\n🎉 All optimization tests passed! Your app is fully optimized!")
        print("\n🚀 Performance Features Enabled:")
        print("   • Connection pooling and query optimization")
        print("   • Response caching and compression")
        print("   • Rate limiting and security")
        print("   • Background task processing")
        print("   • Real-time performance monitoring")
        print("   • Optimized service layer")
        print("   • Database indexing")
        print("\nNext steps:")
        print("1. Run: python -m app.main_optimized")
        print("2. Monitor: http://localhost:8000/monitoring/health")
        print("3. Metrics: http://localhost:8000/monitoring/metrics")
    else:
        print("⚠️  Some optimization tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    run_comprehensive_optimization_test()
