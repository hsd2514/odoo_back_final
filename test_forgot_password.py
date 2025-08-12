#!/usr/bin/env python3
"""
Test script for forgot password functionality
"""

import asyncio
import json
from datetime import datetime

import httpx


async def test_forgot_password_flow():
    """Test the complete forgot password flow"""
    base_url = "http://localhost:8000"
    
    # Test data
    test_email = "test@example.com"
    new_password = "newpassword123"
    
    async with httpx.AsyncClient() as client:
        print("=== Testing Forgot Password Flow ===\n")
        
        # Step 1: Request password reset
        print("1. Requesting password reset...")
        forgot_response = await client.post(
            f"{base_url}/users/forgot-password",
            json={"email": test_email}
        )
        
        print(f"   Status: {forgot_response.status_code}")
        print(f"   Response: {forgot_response.json()}")
        
        if forgot_response.status_code == 200:
            print("   ✅ Password reset request sent successfully")
        else:
            print("   ❌ Password reset request failed")
            return
        
        print("\n2. Note: In a real scenario, you would:")
        print("   - Check your email for the reset link")
        print("   - Extract the token from the reset link")
        print("   - Use that token to reset your password")
        
        # For demonstration, we'll create a test token
        # (In real usage, this would come from the email)
        from app.utils.jwt import create_password_reset_token
        test_token = create_password_reset_token(test_email)
        print(f"   - Example token: {test_token[:50]}...")
        
        # Step 2: Reset password with token
        print("\n3. Resetting password with token...")
        reset_response = await client.post(
            f"{base_url}/users/reset-password",
            json={
                "token": test_token,
                "new_password": new_password,
                "confirm_password": new_password
            }
        )
        
        print(f"   Status: {reset_response.status_code}")
        print(f"   Response: {reset_response.json()}")
        
        if reset_response.status_code == 200:
            print("   ✅ Password reset successful")
        else:
            print("   ❌ Password reset failed")


def test_email_configuration():
    """Test email configuration and service"""
    print("=== Testing Gmail SMTP Configuration ===\n")
    
    from app.config import get_settings
    from app.utils.email import email_service
    
    settings = get_settings()
    
    print("Gmail SMTP Configuration:")
    print(f"   SMTP Server: {settings.smtp_server}")
    print(f"   SMTP Port: {settings.smtp_port}")
    print(f"   Gmail Username: {settings.smtp_username if settings.smtp_username else 'Not configured'}")
    print(f"   Gmail App Password: {'*' * 16 if settings.smtp_password else 'Not configured'}")
    print(f"   Email From: {settings.email_from}")
    print(f"   Email From Name: {settings.email_from_name}")
    
    if not settings.smtp_username or not settings.smtp_password:
        print("\n⚠️  Gmail SMTP not configured")
        print("   Follow these steps:")
        print("   1. Enable 2-Factor Authentication on your Gmail account")
        print("   2. Generate an App Password for 'Mail'")
        print("   3. Set GMAIL_USERNAME and GMAIL_APP_PASSWORD in your .env file")
        print("   4. See GMAIL_SETUP.md for detailed instructions")
    else:
        print("\n✅ Gmail SMTP configuration looks good")
        
        # Test SMTP connection
        print("\n=== Testing Gmail SMTP Connection ===")
        try:
            import smtplib
            server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.quit()
            print("✅ Gmail SMTP connection successful!")
        except Exception as e:
            print(f"❌ Gmail SMTP connection failed: {str(e)}")
            print("   Check your GMAIL_USERNAME and GMAIL_APP_PASSWORD")
    
    # Test token generation
    print("\n=== Testing Token Generation ===")
    from app.utils.jwt import create_password_reset_token, verify_password_reset_token
    
    test_email = "test@example.com"
    token = create_password_reset_token(test_email)
    print(f"Generated token: {token[:50]}...")
    
    verified_email = verify_password_reset_token(token)
    if verified_email == test_email:
        print("✅ Token generation and verification working correctly")
    else:
        print("❌ Token verification failed")


if __name__ == "__main__":
    print("Gmail SMTP Forgot Password Feature Test\n")
    print("=" * 50)
    
    # Test configuration
    test_email_configuration()
    
    print("\n" + "=" * 50)
    print("\nTo test the full flow:")
    print("1. Configure Gmail SMTP in .env file (see GMAIL_SETUP.md)")
    print("2. Start the server: uvicorn app.main:app --reload")
    print("3. Test via API docs: http://localhost:8000/docs")
    print("4. Use the /users/forgot-password endpoint with a real email")
    print("5. Check your Gmail inbox for the password reset email")
    print("\nFor automated testing:")
    print('python -c "import asyncio; from test_forgot_password import test_forgot_password_flow; asyncio.run(test_forgot_password_flow())"')
