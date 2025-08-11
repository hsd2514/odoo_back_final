"""
Celery Background Task Processing for Peak Performance
Handles async operations like email notifications, reports, and heavy computations
"""
from __future__ import annotations

import logging
import smtplib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json

try:
    from celery import Celery
    from celery.result import AsyncResult
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

from ..config import get_settings
from ..database_optimized import SessionLocal
from ..models.rentals import RentalOrder, Notification
from ..models.user import User

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """High-performance background task manager"""
    
    def __init__(self):
        self.celery_app = None
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.task_queue = []
        self.enabled = False
        
        if CELERY_AVAILABLE:
            try:
                # Initialize Celery with Redis broker
                self.celery_app = Celery(
                    'odoo_rental_tasks',
                    broker='redis://localhost:6379/1',
                    backend='redis://localhost:6379/1',
                    include=['app.utils.celery_tasks']
                )
                
                # Configure Celery
                self.celery_app.conf.update(
                    task_serializer='json',
                    accept_content=['json'],
                    result_serializer='json',
                    timezone='UTC',
                    enable_utc=True,
                    worker_prefetch_multiplier=1,
                    task_acks_late=True,
                    worker_disable_rate_limits=True,
                    task_reject_on_worker_lost=True,
                    task_routes={
                        'send_email_notification': {'queue': 'emails'},
                        'generate_report': {'queue': 'reports'},
                        'cleanup_task': {'queue': 'maintenance'},
                    }
                )
                
                self.enabled = True
                logger.info("✅ Celery background tasks initialized")
                
            except Exception as e:
                logger.warning(f"⚠️ Celery not available: {e}")
        
        if not self.enabled:
            logger.info("📋 Using thread pool for background tasks")
    
    def send_email_async(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        priority: str = "normal"
    ) -> str:
        """Send email notification asynchronously"""
        if self.enabled and self.celery_app:
            # Use Celery for true async processing
            result = self.celery_app.send_task(
                'send_email_notification',
                args=[to_email, subject, body, html_body],
                kwargs={'priority': priority},
                queue='emails'
            )
            return result.id
        else:
            # Fallback to thread pool
            future = self.thread_pool.submit(
                self._send_email_sync, to_email, subject, body, html_body
            )
            return f"thread_{id(future)}"
    
    def _send_email_sync(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """Synchronous email sending"""
        try:
            settings = get_settings()
            
            if not settings.smtp_username or not settings.smtp_password:
                logger.warning("⚠️ SMTP credentials not configured")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.email_from
            msg['To'] = to_email
            
            # Add text part
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✅ Email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
            return False
    
    def generate_report_async(
        self,
        report_type: str,
        parameters: Dict[str, Any],
        user_id: int
    ) -> str:
        """Generate reports asynchronously"""
        if self.enabled and self.celery_app:
            result = self.celery_app.send_task(
                'generate_report',
                args=[report_type, parameters, user_id],
                queue='reports'
            )
            return result.id
        else:
            future = self.thread_pool.submit(
                self._generate_report_sync, report_type, parameters, user_id
            )
            return f"thread_{id(future)}"
    
    def _generate_report_sync(
        self,
        report_type: str,
        parameters: Dict[str, Any],
        user_id: int
    ) -> Dict[str, Any]:
        """Synchronous report generation"""
        try:
            start_time = datetime.now()
            
            with SessionLocal() as db:
                if report_type == "rental_summary":
                    return self._generate_rental_summary_report(db, parameters)
                elif report_type == "inventory_status":
                    return self._generate_inventory_report(db, parameters)
                elif report_type == "revenue_analysis":
                    return self._generate_revenue_report(db, parameters)
                else:
                    raise ValueError(f"Unknown report type: {report_type}")
                    
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")
            return {"error": str(e)}
    
    def _generate_rental_summary_report(
        self, 
        db: SessionLocal, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate rental summary report"""
        days = parameters.get('days', 30)
        seller_id = parameters.get('seller_id')
        
        # Use optimized query
        from .advanced_query_optimizer import query_optimizer
        
        analytics = query_optimizer.get_rental_analytics_optimized(
            seller_id=seller_id,
            days=days
        )
        
        return {
            "report_type": "rental_summary",
            "generated_at": datetime.now().isoformat(),
            "parameters": parameters,
            "data": analytics
        }
    
    def _generate_inventory_report(
        self, 
        db: SessionLocal, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate inventory status report"""
        from ..models.inventory import InventoryItem
        from ..models.catalog import Product
        from sqlalchemy import func
        
        # Get inventory statistics
        inventory_stats = db.query(
            Product.product_id,
            Product.title,
            func.count(InventoryItem.item_id).label('total_items'),
            func.count(InventoryItem.item_id).filter(
                InventoryItem.status == 'available'
            ).label('available_items'),
            func.count(InventoryItem.item_id).filter(
                InventoryItem.status == 'reserved'
            ).label('reserved_items'),
            func.count(InventoryItem.item_id).filter(
                InventoryItem.status == 'rented'
            ).label('rented_items')
        ).join(
            InventoryItem, Product.product_id == InventoryItem.product_id
        ).group_by(
            Product.product_id, Product.title
        ).all()
        
        return {
            "report_type": "inventory_status",
            "generated_at": datetime.now().isoformat(),
            "data": [
                {
                    "product_id": stat.product_id,
                    "product_title": stat.title,
                    "total_items": stat.total_items,
                    "available_items": stat.available_items,
                    "reserved_items": stat.reserved_items,
                    "rented_items": stat.rented_items,
                    "utilization_rate": (stat.rented_items + stat.reserved_items) / stat.total_items * 100 if stat.total_items > 0 else 0
                }
                for stat in inventory_stats
            ]
        }
    
    def _generate_revenue_report(
        self, 
        db: SessionLocal, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate revenue analysis report"""
        from sqlalchemy import text
        
        days = parameters.get('days', 30)
        
        # Daily revenue analysis
        daily_revenue = db.execute(text("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as order_count,
                SUM(total_amount) as revenue,
                AVG(total_amount) as avg_order_value
            FROM rental_orders 
            WHERE created_at >= NOW() - INTERVAL :days DAY
            AND status IN ('booked', 'ongoing', 'completed')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """), {'days': days}).all()
        
        return {
            "report_type": "revenue_analysis",
            "generated_at": datetime.now().isoformat(),
            "period_days": days,
            "data": [
                {
                    "date": str(row.date),
                    "order_count": row.order_count,
                    "revenue": float(row.revenue),
                    "avg_order_value": float(row.avg_order_value)
                }
                for row in daily_revenue
            ]
        }
    
    def cleanup_old_data_async(self, days_old: int = 90) -> str:
        """Clean up old data asynchronously"""
        if self.enabled and self.celery_app:
            result = self.celery_app.send_task(
                'cleanup_task',
                args=[days_old],
                queue='maintenance'
            )
            return result.id
        else:
            future = self.thread_pool.submit(self._cleanup_old_data_sync, days_old)
            return f"thread_{id(future)}"
    
    def _cleanup_old_data_sync(self, days_old: int) -> Dict[str, int]:
        """Synchronous data cleanup"""
        try:
            with SessionLocal() as db:
                cutoff_date = datetime.now() - timedelta(days=days_old)
                
                # Clean up old notifications
                old_notifications = db.query(Notification).filter(
                    Notification.created_at < cutoff_date,
                    Notification.sent == True
                ).count()
                
                db.query(Notification).filter(
                    Notification.created_at < cutoff_date,
                    Notification.sent == True
                ).delete()
                
                # Clean up completed rental orders older than retention period
                old_rentals = db.query(RentalOrder).filter(
                    RentalOrder.end_ts < cutoff_date,
                    RentalOrder.status == 'completed'
                ).count()
                
                # Archive instead of delete (for compliance)
                db.query(RentalOrder).filter(
                    RentalOrder.end_ts < cutoff_date,
                    RentalOrder.status == 'completed'
                ).update({"status": "archived"})
                
                db.commit()
                
                logger.info(f"✅ Cleanup completed: {old_notifications} notifications, {old_rentals} rentals archived")
                
                return {
                    "notifications_cleaned": old_notifications,
                    "rentals_archived": old_rentals
                }
                
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return {"error": str(e)}
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of background task"""
        if self.enabled and self.celery_app and not task_id.startswith("thread_"):
            try:
                result = AsyncResult(task_id, app=self.celery_app)
                return {
                    "task_id": task_id,
                    "status": result.status,
                    "result": result.result if result.ready() else None,
                    "traceback": result.traceback if result.failed() else None
                }
            except Exception as e:
                return {"task_id": task_id, "status": "ERROR", "error": str(e)}
        else:
            return {"task_id": task_id, "status": "UNKNOWN", "note": "Thread pool task"}
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get background task queue statistics"""
        if self.enabled and self.celery_app:
            try:
                # Get Celery stats
                inspect = self.celery_app.control.inspect()
                active_tasks = inspect.active()
                scheduled_tasks = inspect.scheduled()
                
                return {
                    "celery_enabled": True,
                    "active_tasks": len(active_tasks.get('celery@worker', [])) if active_tasks else 0,
                    "scheduled_tasks": len(scheduled_tasks.get('celery@worker', [])) if scheduled_tasks else 0,
                    "worker_status": "online" if active_tasks is not None else "offline"
                }
            except Exception as e:
                return {"celery_enabled": True, "error": str(e)}
        else:
            return {
                "celery_enabled": False,
                "thread_pool_size": self.thread_pool._max_workers,
                "fallback_mode": True
            }

# Notification templates
class NotificationTemplates:
    """Email notification templates"""
    
    @staticmethod
    def rental_confirmation(rental_order: RentalOrder, user: User) -> tuple[str, str, str]:
        """Rental confirmation email template"""
        subject = f"Rental Confirmation - Order #{rental_order.rental_id}"
        
        text_body = f"""
        Dear {user.first_name},
        
        Your rental order #{rental_order.rental_id} has been confirmed!
        
        Rental Period: {rental_order.start_ts.strftime('%Y-%m-%d')} to {rental_order.end_ts.strftime('%Y-%m-%d')}
        Total Amount: ${rental_order.total_amount:.2f}
        Status: {rental_order.status}
        
        Thank you for choosing our rental service!
        
        Best regards,
        Odoo Rental Team
        """
        
        html_body = f"""
        <h2>Rental Confirmation</h2>
        <p>Dear {user.first_name},</p>
        <p>Your rental order <strong>#{rental_order.rental_id}</strong> has been confirmed!</p>
        
        <div style="background-color: #f5f5f5; padding: 15px; margin: 15px 0;">
            <h3>Order Details</h3>
            <p><strong>Rental Period:</strong> {rental_order.start_ts.strftime('%Y-%m-%d')} to {rental_order.end_ts.strftime('%Y-%m-%d')}</p>
            <p><strong>Total Amount:</strong> ${rental_order.total_amount:.2f}</p>
            <p><strong>Status:</strong> <span style="color: green;">{rental_order.status}</span></p>
        </div>
        
        <p>Thank you for choosing our rental service!</p>
        <p>Best regards,<br>Odoo Rental Team</p>
        """
        
        return subject, text_body, html_body
    
    @staticmethod
    def payment_confirmation(payment_amount: float, user: User) -> tuple[str, str, str]:
        """Payment confirmation email template"""
        subject = "Payment Confirmation - Rental Service"
        
        text_body = f"""
        Dear {user.first_name},
        
        We have successfully received your payment of ${payment_amount:.2f}.
        
        Your rental order will be processed shortly.
        
        Thank you for your business!
        
        Best regards,
        Odoo Rental Team
        """
        
        html_body = f"""
        <h2>Payment Confirmation</h2>
        <p>Dear {user.first_name},</p>
        <p>We have successfully received your payment of <strong>${payment_amount:.2f}</strong>.</p>
        <p>Your rental order will be processed shortly.</p>
        <p>Thank you for your business!</p>
        <p>Best regards,<br>Odoo Rental Team</p>
        """
        
        return subject, text_body, html_body

# Global task manager instance
task_manager = BackgroundTaskManager()

# Convenience functions for common operations
def send_rental_confirmation_email(rental_id: int) -> str:
    """Send rental confirmation email"""
    with SessionLocal() as db:
        rental = db.query(RentalOrder).filter(RentalOrder.rental_id == rental_id).first()
        user = db.query(User).filter(User.user_id == rental.customer_id).first()
        
        if rental and user:
            subject, text_body, html_body = NotificationTemplates.rental_confirmation(rental, user)
            return task_manager.send_email_async(
                to_email=user.email,
                subject=subject,
                body=text_body,
                html_body=html_body,
                priority="high"
            )
    return ""

def send_payment_confirmation_email(user_id: int, amount: float) -> str:
    """Send payment confirmation email"""
    with SessionLocal() as db:
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if user:
            subject, text_body, html_body = NotificationTemplates.payment_confirmation(amount, user)
            return task_manager.send_email_async(
                to_email=user.email,
                subject=subject,
                body=text_body,
                html_body=html_body,
                priority="high"
            )
    return ""

# Setup function for application startup
def setup_advanced_background_tasks():
    """Setup advanced background task processing"""
    logger.info("🚀 Setting up advanced background tasks...")
    
    if task_manager.enabled:
        logger.info("✅ Celery task manager ready")
    else:
        logger.info("📋 Thread pool task manager ready")
    
    return task_manager.enabled

# Export main components
__all__ = [
    'BackgroundTaskManager', 'task_manager', 'NotificationTemplates',
    'send_rental_confirmation_email', 'send_payment_confirmation_email',
    'setup_advanced_background_tasks'
]
