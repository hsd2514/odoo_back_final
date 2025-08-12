from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from ..utils.email import email_service

router = APIRouter(prefix="/test", tags=["test"])

@router.post("/send-test-email")
async def send_test_email():
    """Send a test email to verify email configuration."""
    try:
        # Test email configuration
        success = email_service.send_email(
            to_emails=["test@example.com"],
            subject="Test Email - Odoo Rental System",
            html_content="""
            <h1>Test Email</h1>
            <p>This is a test email to verify the email configuration is working.</p>
            <p>If you receive this, the email service is properly configured.</p>
            """,
            text_content="Test Email - Odoo Rental System\n\nThis is a test email to verify the email configuration is working."
        )
        
        if success:
            return {"message": "Test email sent successfully", "status": "success"}
        else:
            return {"message": "Failed to send test email", "status": "failed"}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email test failed: {str(e)}"
        )

@router.post("/send-password-reset-test")
async def send_password_reset_test():
    """Send a test password reset email."""
    try:
        # Test password reset email
        success = email_service.send_password_reset_email(
            email="test@example.com",
            reset_token="test-token-12345",
            user_name="Test User"
        )
        
        if success:
            return {"message": "Password reset test email sent successfully", "status": "success"}
        else:
            return {"message": "Failed to send password reset test email", "status": "failed"}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset test failed: {str(e)}"
        )


@router.post("/setup-test-promotions")
async def setup_test_promotions():
    """Setup test promotion codes for development."""
    try:
        from ..routers.promos_loyalty import setup_test_promotions
        result = setup_test_promotions()
        return {"message": "Test promotions setup completed", "result": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test promotions setup failed: {str(e)}"
        )


@router.get("/check-promotions")
async def check_promotions():
    """Check existing promotions in the database."""
    try:
        from ..database import get_db
        from ..models.promotions import Promotion
        from sqlalchemy.orm import Session
        
        db = next(get_db())
        promos = db.query(Promotion).all()
        
        return {
            "message": f"Found {len(promos)} promotions",
            "promotions": [
                {
                    "promo_id": p.promo_id,
                    "code": p.code,
                    "discount_type": p.discount_type,
                    "value": float(p.value),
                    "valid_from": str(p.valid_from),
                    "valid_to": str(p.valid_to)
                }
                for p in promos
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check promotions: {str(e)}"
        )
