from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from ..config import get_settings


class EmailService:
    def __init__(self):
        self.settings = get_settings()
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send email using SMTP configuration
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content (optional)
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.settings.email_from_name} <{self.settings.email_from}>"
            msg['To'] = ", ".join(to_emails)
            
            # Add text content if provided
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.settings.smtp_server, self.settings.smtp_port) as server:
                server.starttls()
                if self.settings.smtp_username and self.settings.smtp_password:
                    server.login(self.settings.smtp_username, self.settings.smtp_password)
                
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Email sending failed: {str(e)}")
            return False
    
    def send_password_reset_email(self, email: str, reset_token: str, user_name: str = "") -> bool:
        """
        Send password reset email with reset link
        
        Args:
            email: Recipient email address
            reset_token: Password reset token
            user_name: User's name for personalization
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        subject = "Password Reset Request - Odoo Rental System"
        
        # In a real application, this would be your frontend URL
        reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
        
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


# Singleton instance
email_service = EmailService()
