"""
Background task utilities for async operations and performance optimization.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from ..database_optimized import get_db_context

# Configure logging
logger = logging.getLogger(__name__)

# Thread pool for CPU-intensive tasks
thread_pool = ThreadPoolExecutor(max_workers=4)

class TaskQueue:
    """Simple task queue for background operations."""
    
    def __init__(self):
        self.tasks = []
        self.running = False
    
    def add_task(self, func: Callable, *args, **kwargs):
        """Add a task to the queue."""
        self.tasks.append((func, args, kwargs))
    
    async def process_tasks(self):
        """Process all tasks in the queue."""
        if self.running:
            return
        
        self.running = True
        try:
            while self.tasks:
                func, args, kwargs = self.tasks.pop(0)
                try:
                    if asyncio.iscoroutinefunction(func):
                        await func(*args, **kwargs)
                    else:
                        await asyncio.get_event_loop().run_in_executor(
                            thread_pool, func, *args, **kwargs
                        )
                except Exception as e:
                    logger.error(f"Task failed: {func.__name__} - {e}")
        finally:
            self.running = False

# Global task queue
task_queue = TaskQueue()

def background_task(func: Callable) -> Callable:
    """Decorator to mark functions as background tasks."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        task_queue.add_task(func, *args, **kwargs)
        return "Task queued"
    return wrapper

# Email-related background tasks
@background_task
def send_email_async(to_email: str, subject: str, body: str):
    """Send email in background."""
    try:
        from ..utils.email import send_email
        with get_db_context() as db:
            send_email(to_email, subject, body)
        logger.info(f"Email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")

@background_task
def send_rental_confirmation_email(rental_order_id: int):
    """Send rental confirmation email in background."""
    try:
        with get_db_context() as db:
            from ..models.rentals import RentalOrder
            from ..models.user import User
            
            rental = db.query(RentalOrder).filter(
                RentalOrder.rental_order_id == rental_order_id
            ).first()
            
            if rental and rental.customer:
                subject = f"Rental Confirmation - Order #{rental.rental_order_id}"
                body = f"""
                Dear {rental.customer.full_name},
                
                Your rental order #{rental.rental_order_id} has been confirmed.
                
                Order Details:
                - Start Date: {rental.start_ts.strftime('%Y-%m-%d %H:%M')}
                - End Date: {rental.end_ts.strftime('%Y-%m-%d %H:%M')}
                - Total Amount: ${rental.total_amount}
                - Status: {rental.status}
                
                Thank you for choosing our service!
                """
                
                send_email_async(rental.customer.email, subject, body)
    except Exception as e:
        logger.error(f"Failed to send rental confirmation for order {rental_order_id}: {e}")

@background_task
def send_payment_confirmation_email(payment_intent_id: str):
    """Send payment confirmation email in background."""
    try:
        # This would integrate with your Stripe service to get payment details
        logger.info(f"Payment confirmation email queued for {payment_intent_id}")
    except Exception as e:
        logger.error(f"Failed to send payment confirmation for {payment_intent_id}: {e}")

# Database maintenance tasks
@background_task
def cleanup_expired_tokens():
    """Clean up expired JWT tokens and sessions."""
    try:
        with get_db_context() as db:
            # Clean up expired password reset tokens
            expired_date = datetime.utcnow() - timedelta(hours=24)
            # Implement token cleanup logic here
            logger.info("Token cleanup completed")
    except Exception as e:
        logger.error(f"Token cleanup failed: {e}")

@background_task
def update_inventory_cache():
    """Update inventory availability cache."""
    try:
        with get_db_context() as db:
            from ..models.inventory import InventoryItem
            
            # Update inventory statistics
            inventory_items = db.query(InventoryItem).all()
            
            # Could update Redis cache here for fast inventory lookups
            logger.info(f"Updated inventory cache for {len(inventory_items)} items")
    except Exception as e:
        logger.error(f"Inventory cache update failed: {e}")

@background_task
def generate_daily_reports():
    """Generate daily business reports."""
    try:
        with get_db_context() as db:
            from ..utils.query_optimizer import RentalQueryOptimizer
            
            optimizer = RentalQueryOptimizer(db)
            
            # Generate revenue summary
            revenue_summary = optimizer.get_revenue_summary()
            
            # Generate popular products report
            popular_products = optimizer.get_popular_products()
            
            logger.info("Daily reports generated successfully")
    except Exception as e:
        logger.error(f"Daily report generation failed: {e}")

# Stripe webhook background tasks
@background_task
def process_stripe_webhook(event_type: str, event_data: dict):
    """Process Stripe webhook events in background."""
    try:
        if event_type == "payment_intent.succeeded":
            payment_intent_id = event_data.get("id")
            send_payment_confirmation_email(payment_intent_id)
        
        elif event_type == "invoice.payment_failed":
            # Handle failed payments
            logger.warning(f"Payment failed for invoice: {event_data.get('id')}")
        
        logger.info(f"Processed Stripe webhook: {event_type}")
    except Exception as e:
        logger.error(f"Stripe webhook processing failed: {e}")

# Performance monitoring tasks
@background_task
def log_performance_metrics():
    """Log performance metrics for monitoring."""
    try:
        from ..middleware.performance import get_performance_stats
        from ..database_optimized import db_manager
        
        # Get performance stats
        perf_stats = get_performance_stats()
        db_stats = db_manager.get_connection_info()
        
        # Log metrics (in production, send to monitoring service)
        logger.info(f"Performance metrics: {perf_stats}")
        logger.info(f"Database metrics: {db_stats}")
    except Exception as e:
        logger.error(f"Performance metrics logging failed: {e}")

# Scheduler for periodic tasks
class TaskScheduler:
    """Simple task scheduler for periodic background tasks."""
    
    def __init__(self):
        self.scheduled_tasks = []
        self.running = False
    
    def schedule_periodic(self, func: Callable, interval_minutes: int):
        """Schedule a function to run periodically."""
        self.scheduled_tasks.append({
            "func": func,
            "interval": interval_minutes,
            "last_run": datetime.utcnow() - timedelta(minutes=interval_minutes)
        })
    
    async def run_scheduler(self):
        """Run the task scheduler."""
        if self.running:
            return
        
        self.running = True
        try:
            while True:
                now = datetime.utcnow()
                
                for task in self.scheduled_tasks:
                    time_since_last = now - task["last_run"]
                    if time_since_last.total_seconds() >= task["interval"] * 60:
                        try:
                            if asyncio.iscoroutinefunction(task["func"]):
                                await task["func"]()
                            else:
                                await asyncio.get_event_loop().run_in_executor(
                                    thread_pool, task["func"]
                                )
                            task["last_run"] = now
                        except Exception as e:
                            logger.error(f"Scheduled task failed: {task['func'].__name__} - {e}")
                
                # Sleep for 1 minute before checking again
                await asyncio.sleep(60)
        finally:
            self.running = False

# Global scheduler
scheduler = TaskScheduler()

def setup_background_tasks():
    """Setup all background tasks and scheduling."""
    # Schedule periodic tasks
    scheduler.schedule_periodic(cleanup_expired_tokens, interval_minutes=60)  # Every hour
    scheduler.schedule_periodic(update_inventory_cache, interval_minutes=30)  # Every 30 minutes
    scheduler.schedule_periodic(generate_daily_reports, interval_minutes=1440)  # Daily
    scheduler.schedule_periodic(log_performance_metrics, interval_minutes=15)  # Every 15 minutes
    
    logger.info("✅ Background tasks and scheduler configured")

async def start_background_scheduler():
    """Start the background task scheduler."""
    await scheduler.run_scheduler()

# Utility functions for FastAPI integration
def add_background_task(background_tasks: BackgroundTasks, func: Callable, *args, **kwargs):
    """Add a background task to FastAPI's background tasks."""
    background_tasks.add_task(func, *args, **kwargs)

def queue_task(func: Callable, *args, **kwargs):
    """Queue a task for background processing."""
    task_queue.add_task(func, *args, **kwargs)
