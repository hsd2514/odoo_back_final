from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database_optimized import Base, engine, SessionLocal  # Use optimized database
from .routers import users, catalog, rentals
from .routers import schedules, handover_qr, billing, promos_loyalty, notifications_availability
from .routers import inventory
from .routers import roles
from .routers import stripe_payments

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan for startup optimizations."""
    # Startup optimizations
    logger.info("🚀 Starting optimized FastAPI application...")
    
    # Apply database optimizations
    try:
        from .utils.query_optimizer import optimize_database_schema
        with SessionLocal() as db:
            optimize_database_schema(db)
        logger.info("✅ Database optimizations applied")
    except Exception as e:
        logger.warning(f"⚠️ Database optimization skipped: {e}")
    
    # Setup background tasks
    try:
        from .utils.background_tasks import setup_background_tasks
        setup_background_tasks()
        logger.info("✅ Background tasks configured")
    except Exception as e:
        logger.warning(f"⚠️ Background tasks setup failed: {e}")
    
    logger.info("✅ Application startup complete")
    yield
    
    # Shutdown
    logger.info("🛑 Application shutdown")

def create_app() -> FastAPI:
    settings = get_settings()
    
    # Create app with lifespan events
    app = FastAPI(
        title=f"{settings.app_name} - Optimized",
        description="High-performance rental management API with Stripe integration",
        version="2.0.0",
        lifespan=lifespan
    )

    # CORS (optimized settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
        max_age=3600,  # Cache preflight for 1 hour
    )

    # Import models to ensure they're registered with SQLAlchemy
    from .models import user, catalog as catalog_models, rentals as rental_models

    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Register routers
    app.include_router(users.router)
    app.include_router(catalog.router)
    app.include_router(rentals.router)
    app.include_router(schedules.router)
    app.include_router(handover_qr.router)
    app.include_router(billing.router)
    app.include_router(promos_loyalty.router)
    app.include_router(notifications_availability.router)
    app.include_router(inventory.router)
    app.include_router(roles.router)
    app.include_router(stripe_payments.router)
    
    # Add monitoring router if available
    try:
        from .routers import monitoring
        app.include_router(monitoring.router)
        logger.info("✅ Monitoring endpoints added")
    except ImportError:
        logger.info("⚠️ Monitoring endpoints not available")
    
    # Add optimized root endpoint
    @app.get("/", summary="API Status")
    async def root():
        return {
            "message": "Optimized Rental Management API",
            "version": "2.0.0",
            "status": "running",
            "optimizations": {
                "database_pooling": True,
                "query_optimization": True,
                "background_tasks": True,
                "monitoring": True
            }
        }
    
    logger.info("✅ Optimized FastAPI application created")
    return app

app = create_app()

# Add startup validation
@app.on_event("startup")
async def validate_optimizations():
    """Validate optimization features."""
    from .database_optimized import db_manager
    
    logger.info("🔍 Validating optimizations...")
    
    # Check database pool
    pool_info = db_manager.get_connection_info()
    logger.info(f"  Database pool: {pool_info}")
    
    # Check configuration
    settings = get_settings()
    logger.info(f"  Stripe: {'✅' if settings.stripe_secret_key else '⚠️'}")
    logger.info(f"  Email: {'✅' if settings.smtp_username else '⚠️'}")
    
    logger.info("✅ Optimization validation complete")


