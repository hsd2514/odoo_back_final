"""
Optimized database configuration with connection pooling,
query optimization, and performance enhancements.
"""

from __future__ import annotations

import logging
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from .config import get_settings

# Configure logging for SQL queries (enable in development)
logging.basicConfig()
sql_logger = logging.getLogger('sqlalchemy.engine')

class Base(DeclarativeBase):
    pass

def _make_engine_url() -> str:
    settings = get_settings()
    return settings.database_url

def _create_optimized_engine():
    """Create an optimized SQLAlchemy engine with connection pooling."""
    settings = get_settings()
    url = _make_engine_url()
    
    # Base engine configuration
    engine_kwargs = {
        "pool_pre_ping": True,  # Verify connections before use
        "pool_recycle": 3600,   # Recycle connections every hour
        "echo": False,          # Set to True for SQL query logging in development
    }
    
    # Database-specific optimizations
    if url.startswith("sqlite"):
        engine_kwargs.update({
            "connect_args": {"check_same_thread": False},
            "poolclass": pool.StaticPool,
        })
    else:
        # PostgreSQL/MySQL optimizations
        engine_kwargs.update({
            "poolclass": QueuePool,
            "pool_size": 20,        # Number of connections to maintain
            "max_overflow": 30,     # Additional connections if pool is full
            "pool_timeout": 30,     # Timeout for getting connection from pool
            "pool_reset_on_return": "commit",  # Reset connection state
        })
    
    engine = create_engine(url, **engine_kwargs)
    
    # Add connection event listeners for monitoring
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if url.startswith("sqlite"):
            cursor = dbapi_connection.cursor()
            # SQLite performance optimizations
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL") 
            cursor.execute("PRAGMA cache_size=1000")
            cursor.execute("PRAGMA temp_store=memory")
            cursor.close()
    
    @event.listens_for(engine, "checkout")
    def checkout_listener(dbapi_connection, connection_record, connection_proxy):
        """Log connection checkout for monitoring."""
        pass  # Can add monitoring logic here
    
    return engine

# Create optimized engine
engine = _create_optimized_engine()

# Optimized session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,      # Manual control over flushing
    autocommit=False,     # Manual transaction control
    expire_on_commit=True # Prevent lazy loading issues
)

def get_db() -> Generator[Session, None, None]:
    """Optimized database session dependency with proper error handling."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

@contextmanager
def get_db_context():
    """Context manager for database sessions outside of FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

class DatabaseManager:
    """Database manager for advanced operations and monitoring."""
    
    @staticmethod
    def get_connection_info():
        """Get current database connection pool information."""
        return {
            "pool_size": engine.pool.size() if hasattr(engine.pool, 'size') else 'N/A',
            "checked_in": engine.pool.checkedin() if hasattr(engine.pool, 'checkedin') else 'N/A',
            "checked_out": engine.pool.checkedout() if hasattr(engine.pool, 'checkedout') else 'N/A',
            "overflow": engine.pool.overflow() if hasattr(engine.pool, 'overflow') else 'N/A',
        }
    
    @staticmethod
    def enable_query_logging():
        """Enable SQL query logging for debugging."""
        sql_logger.setLevel(logging.INFO)
    
    @staticmethod
    def disable_query_logging():
        """Disable SQL query logging."""
        sql_logger.setLevel(logging.WARNING)

# Global database manager instance
db_manager = DatabaseManager()
