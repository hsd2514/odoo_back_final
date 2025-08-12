#!/usr/bin/env python3
"""
Quick setup script for Gmail SMTP configuration
"""

import os
import sys


def create_env_file():
    """Create .env file with Gmail configuration prompts"""
    print("🔧 Gmail SMTP Setup for Odoo Rental System")
    print("=" * 50)
    
    if os.path.exists('.env'):
        response = input("\n⚠️  .env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            return
    
    print("\n📧 Gmail Configuration Setup")
    print("Before proceeding, make sure you have:")
    print("1. ✅ 2-Factor Authentication enabled on Gmail")
    print("2. ✅ Generated an App Password for 'Mail'")
    print("\nIf not, see GMAIL_SETUP.md for detailed instructions.\n")
    
    proceed = input("Ready to proceed? (Y/n): ")
    if proceed.lower() == 'n':
        print("Setup cancelled. Please follow GMAIL_SETUP.md first.")
        return
    
    # Get Gmail credentials
    gmail_username = input("\n📧 Enter your Gmail address: ").strip()
    if not gmail_username:
        print("❌ Gmail address is required!")
        return
    
    gmail_app_password = input("🔑 Enter your Gmail App Password (16 characters): ").strip()
    if not gmail_app_password:
        print("❌ Gmail App Password is required!")
        return
    
    # Remove spaces from app password (common mistake)
    gmail_app_password = gmail_app_password.replace(' ', '')
    
    if len(gmail_app_password) != 16:
        print(f"⚠️  Warning: App Password should be 16 characters, got {len(gmail_app_password)}")
        print("Make sure you copied the full App Password from Google")
    
    # Get other settings
    from_name = input(f"👤 Sender name [Odoo Rental System]: ").strip() or "Odoo Rental System"
    
    # Create .env content
    env_content = f"""# Database Configuration
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/odoo_final

# Security Configuration
SECRET_KEY=dev-secret-key-change-me-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_ALGORITHM=HS256
PASSWORD_RESET_EXPIRE_MINUTES=15

# Gmail SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
GMAIL_USERNAME={gmail_username}
GMAIL_APP_PASSWORD={gmail_app_password}
EMAIL_FROM={gmail_username}
EMAIL_FROM_NAME={from_name}

# Application Configuration
APP_NAME=Odoo Rental Management System
"""
    
    # Write .env file
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("\n✅ .env file created successfully!")
        
        # Test the configuration
        print("\n🧪 Testing Gmail SMTP connection...")
        test_smtp_connection(gmail_username, gmail_app_password)
        
    except Exception as e:
        print(f"\n❌ Error creating .env file: {e}")
        return
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Start the server: uvicorn app.main:app --reload")
    print("2. Test at: http://localhost:8000/docs")
    print("3. Try the /users/forgot-password endpoint")


def test_smtp_connection(username, password):
    """Test SMTP connection with provided credentials"""
    try:
        import smtplib
        
        print("   Connecting to Gmail SMTP...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        
        print("   Authenticating...")
        server.login(username, password)
        server.quit()
        
        print("   ✅ Gmail SMTP connection successful!")
        
    except smtplib.SMTPAuthenticationError:
        print("   ❌ Authentication failed!")
        print("   Check your Gmail username and App Password")
        print("   Make sure 2FA is enabled and you're using an App Password")
        
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        print("   Check your internet connection and Gmail settings")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Test existing configuration
        if not os.path.exists('.env'):
            print("❌ No .env file found. Run without --test to create one.")
            return
        
        print("🧪 Testing existing Gmail configuration...")
        os.system('python test_forgot_password.py')
    else:
        # Create new configuration
        create_env_file()


if __name__ == "__main__":
    main()
