"""
Optimized FastAPI application with performance enhancements.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database_optimized import Base, engine
from .middleware.performance import add_performance_middleware
from .utils.background_tasks import setup_background_tasks, start_background_scheduler
from .utils.query_optimizer import optimize_database_schema
from .database_optimized import SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events for startup and shutdown."""
    # Startup
    logger.info("🚀 Starting FastAPI application...")
    
    # Database optimization
    with SessionLocal() as db:
        try:
            optimize_database_schema(db)
            logger.info("✅ Database schema optimized")
        except Exception as e:
            logger.warning(f"⚠️ Database optimization skipped: {e}")
    
    # Setup background tasks
    setup_background_tasks()
    
    # Start background scheduler in a separate task
    scheduler_task = asyncio.create_task(start_background_scheduler())
    
    logger.info("✅ Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down application...")
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    logger.info("✅ Application shutdown complete")

def create_app() -> FastAPI:
    """Create and configure the FastAPI application with optimizations."""
    settings = get_settings()
    
    # Create FastAPI app with lifespan events
    app = FastAPI(
        title=settings.app_name,
        description="Optimized Rental Management API with Stripe Integration",
        version="2.0.0",
        lifespan=lifespan
    )

    # Add performance middleware (order matters!)
    add_performance_middleware(app)

    # CORS configuration (optimized for production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure specific origins in production
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
        max_age=3600,  # Cache preflight requests for 1 hour
    )

    # Import models to ensure they're registered with SQLAlchemy
    from .models import (
        user, catalog, rentals, inventory, 
        billing, promotions, loyalty, subscriptions
    )

    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created/verified")

    # Import and register routers
    from .routers import (
        users, catalog, rentals, schedules, handover_qr,
        billing, promos_loyalty, notifications_availability,
        inventory, roles, stripe_payments, monitoring
    )

    # Register all routers
    routers = [
        (users.router, "Users"),
        (catalog.router, "Catalog"),
        (rentals.router, "Rentals"),
        (schedules.router, "Schedules"),
        (handover_qr.router, "Handover QR"),
        (billing.router, "Billing"),
        (promos_loyalty.router, "Promotions & Loyalty"),
        (notifications_availability.router, "Notifications"),
        (inventory.router, "Inventory"),
        (roles.router, "Roles"),
        (stripe_payments.router, "Stripe Payments"),
        (monitoring.router, "Monitoring"),
    ]

    for router, name in routers:
        app.include_router(router)
        logger.info(f"✅ {name} router registered")

    # Add custom exception handlers
    from fastapi import Request, HTTPException
    from fastapi.responses import JSONResponse

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "timestamp": f"{asyncio.get_event_loop().time():.3f}",
                "path": request.url.path
            }
        )

    @app.exception_handler(500)
    async def internal_server_error_handler(request: Request, exc: Exception):
        logger.error(f"Internal server error: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "timestamp": f"{asyncio.get_event_loop().time():.3f}",
                "path": request.url.path
            }
        )

    # Add health check endpoint
    @app.get("/", summary="Root endpoint")
    async def root():
        return {
            "message": "Optimized Rental Management API",
            "version": "2.0.0",
            "status": "running",
            "features": [
                "Stripe Payment Integration",
                "Gmail SMTP Email Service",
                "Performance Monitoring",
                "Background Tasks",
                "Response Caching",
                "Rate Limiting",
                "Query Optimization"
            ]
        }

    # Add startup info endpoint
    @app.get("/info", summary="Application information")
    async def app_info():
        return {
            "app_name": settings.app_name,
            "database": "Connected" if engine else "Not connected",
            "stripe_configured": bool(settings.stripe_secret_key),
            "email_configured": bool(settings.smtp_username),
            "optimizations_enabled": [
                "Connection Pooling",
                "Query Optimization", 
                "Response Caching",
                "Background Tasks",
                "Performance Monitoring",
                "Rate Limiting",
                "Response Compression"
            ]
        }

    logger.info("✅ FastAPI application created successfully")
    return app

# Create the application instance
app = create_app()

# Additional optimization: Add startup validation
@app.on_event("startup")
async def validate_configuration():
    """Validate application configuration on startup."""
    settings = get_settings()
    
    # Log configuration status
    logger.info("🔍 Configuration validation:")
    logger.info(f"  Database: {settings.database_url[:50]}...")
    logger.info(f"  Stripe: {'✅ Configured' if settings.stripe_secret_key else '⚠️ Not configured'}")
    logger.info(f"  Email: {'✅ Configured' if settings.smtp_username else '⚠️ Not configured'}")
    
    # Test database connection
    try:
        with SessionLocal() as db:
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
        logger.info("✅ Database connection verified")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1,  # Use 1 worker for development
        log_level="info"
    )
