"""
Mock Email Service for Development
This service logs emails instead of sending them, useful for development and testing.
"""

import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class MockEmailService:
    """Mock email service that logs emails instead of sending them."""
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Log email instead of sending it.
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content of the email
            
        Returns:
            bool: Always returns True (simulating success)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"=== MOCK EMAIL SENT at {timestamp} ===")
        logger.info(f"To: {', '.join(to_emails)}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Text Content: {text_content}")
        logger.info(f"HTML Content: {html_content}")
        logger.info("=== END MOCK EMAIL ===")
        
        # Also print to console for easy viewing
        print(f"\n{'='*50}")
        print(f"MOCK EMAIL SENT at {timestamp}")
        print(f"To: {', '.join(to_emails)}")
        print(f"Subject: {subject}")
        print(f"Text Content: {text_content}")
        print(f"HTML Content: {html_content}")
        print(f"{'='*50}\n")
        
        return True
    
    def send_password_reset_email(self, email: str, reset_token: str, user_name: str = "") -> bool:
        """
        Log password reset email instead of sending it.
        
        Args:
            email: Recipient email address
            reset_token: Password reset token
            user_name: User's name for personalization
            
        Returns:
            bool: Always returns True (simulating success)
        """
        subject = "Password Reset Request - Odoo Rental System"
        
        # In a real application, this would be your frontend URL
        reset_link = f"http://localhost:3000/auth/reset-password?token={reset_token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #007bff;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f8f9fa;
                    padding: 30px;
                    border-radius: 0 0 5px 5px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #007bff;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <div class="content">
                <p>Hello {user_name if user_name else 'User'},</p>
                
                <p>We received a request to reset your password for your Odoo Rental System account.</p>
                
                <p>Click the button below to reset your password:</p>
                
                <a href="{reset_link}" class="button">Reset Password</a>
                
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #007bff;">{reset_link}</p>
                
                <p><strong>Important:</strong> This link will expire in 15 minutes for security reasons.</p>
                
                <p>If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
                
                <div class="footer">
                    <p>This is an automated message from Odoo Rental System. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Reset Request - Odoo Rental System
        
        Hello {user_name if user_name else 'User'},
        
        We received a request to reset your password for your Odoo Rental System account.
        
        Click this link to reset your password: {reset_link}
        
        Important: This link will expire in 15 minutes for security reasons.
        
        If you didn't request a password reset, please ignore this email.
        
        Best regards,
        Odoo Rental System Team
        """
        
        return self.send_email([email], subject, html_content, text_content)

# Create a mock email service instance
mock_email_service = MockEmailService()
