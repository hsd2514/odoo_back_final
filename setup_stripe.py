#!/usr/bin/env python3
"""
Quick setup script for Stripe payment configuration
"""

import os
import sys


def create_stripe_env():
    """Create .env file with Stripe configuration prompts"""
    print("💳 Stripe Payment Setup for Odoo Rental System")
    print("=" * 50)
    
    # Check if .env exists
    env_exists = os.path.exists('.env')
    if env_exists:
        with open('.env', 'r') as f:
            env_content = f.read()
        
        if 'STRIPE_SECRET_KEY' in env_content:
            response = input("\n⚠️  Stripe configuration already exists in .env. Update? (y/N): ")
            if response.lower() != 'y':
                print("Setup cancelled.")
                return
    
    print("\n💳 Stripe Configuration Setup")
    print("Before proceeding, make sure you have:")
    print("1. ✅ Created a Stripe account at https://stripe.com")
    print("2. ✅ Accessed your Stripe Dashboard")
    print("3. ✅ Found your API keys in Developers → API keys")
    print("\nIf not, see STRIPE_SETUP.md for detailed instructions.\n")
    
    proceed = input("Ready to proceed? (Y/n): ")
    if proceed.lower() == 'n':
        print("Setup cancelled. Please follow STRIPE_SETUP.md first.")
        return
    
    # Get Stripe keys
    print("\n🔑 Stripe API Keys")
    secret_key = input("Enter your Stripe Secret Key (starts with sk_test_ or sk_live_): ").strip()
    if not secret_key:
        print("❌ Secret key is required!")
        return
    
    if not (secret_key.startswith('sk_test_') or secret_key.startswith('sk_live_')):
        print("⚠️  Warning: Secret key should start with sk_test_ or sk_live_")
        print("Make sure you copied the correct key from Stripe Dashboard")
    
    publishable_key = input("Enter your Stripe Publishable Key (starts with pk_test_ or pk_live_): ").strip()
    if not publishable_key:
        print("❌ Publishable key is required!")
        return
    
    if not (publishable_key.startswith('pk_test_') or publishable_key.startswith('pk_live_')):
        print("⚠️  Warning: Publishable key should start with pk_test_ or pk_live_")
        print("Make sure you copied the correct key from Stripe Dashboard")
    
    # Webhook secret (optional)
    webhook_secret = input("Enter your Stripe Webhook Secret (optional, starts with whsec_): ").strip()
    
    # Currency
    currency = input("Enter currency code [usd]: ").strip() or "usd"
    
    # URLs
    success_url = input("Enter success URL [http://localhost:3000/payment/success]: ").strip() or "http://localhost:3000/payment/success"
    cancel_url = input("Enter cancel URL [http://localhost:3000/payment/cancel]: ").strip() or "http://localhost:3000/payment/cancel"
    
    # Create or update .env content
    stripe_config = f"""
# Stripe Payment Configuration
STRIPE_SECRET_KEY={secret_key}
STRIPE_PUBLISHABLE_KEY={publishable_key}
STRIPE_WEBHOOK_SECRET={webhook_secret}
STRIPE_CURRENCY={currency}
PAYMENT_SUCCESS_URL={success_url}
PAYMENT_CANCEL_URL={cancel_url}
"""
    
    try:
        if env_exists:
            # Update existing .env file
            with open('.env', 'r') as f:
                env_content = f.read()
            
            # Remove existing Stripe configuration
            lines = env_content.split('\n')
            filtered_lines = []
            in_stripe_section = False
            
            for line in lines:
                if line.strip() == "# Stripe Payment Configuration":
                    in_stripe_section = True
                    continue
                elif line.startswith('#') and in_stripe_section:
                    in_stripe_section = False
                elif line.startswith('STRIPE_') or line.startswith('PAYMENT_'):
                    continue
                
                if not in_stripe_section:
                    filtered_lines.append(line)
            
            # Add new Stripe configuration
            updated_content = '\n'.join(filtered_lines).rstrip() + stripe_config
            
            with open('.env', 'w') as f:
                f.write(updated_content)
        else:
            # Create new .env file with basic configuration
            env_content = f"""# Database Configuration
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/odoo_final

# Security Configuration
SECRET_KEY=dev-secret-key-change-me-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_ALGORITHM=HS256
PASSWORD_RESET_EXPIRE_MINUTES=15

# Application Configuration
APP_NAME=Odoo Rental Management System
{stripe_config}"""
            
            with open('.env', 'w') as f:
                f.write(env_content)
        
        print("\n✅ .env file updated successfully!")
        
        # Test the configuration
        print("\n🧪 Testing Stripe configuration...")
        test_stripe_config(secret_key, publishable_key)
        
    except Exception as e:
        print(f"\n❌ Error updating .env file: {e}")
        return
    
    print("\n🎉 Stripe setup complete!")
    print("\nNext steps:")
    print("1. Start the server: uvicorn app.main:app --reload")
    print("2. Test at: http://localhost:8000/docs")
    print("3. Look for endpoints under 'stripe-payments' tag")
    print("4. Use test card 4242424242424242 for testing")


def test_stripe_config(secret_key, publishable_key):
    """Test Stripe configuration"""
    try:
        # Set environment variables temporarily for testing
        os.environ['STRIPE_SECRET_KEY'] = secret_key
        os.environ['STRIPE_PUBLISHABLE_KEY'] = publishable_key
        
        import stripe
        stripe.api_key = secret_key
        
        # Test API connection
        account = stripe.Account.retrieve()
        print(f"   ✅ Stripe connection successful!")
        print(f"   Account ID: {account.id}")
        print(f"   Country: {account.country}")
        print(f"   Currency: {account.default_currency}")
        
        # Test key types
        if secret_key.startswith('sk_test_'):
            print("   📝 Using TEST mode - safe for development")
        elif secret_key.startswith('sk_live_'):
            print("   🚨 Using LIVE mode - real payments will be processed!")
        
    except Exception as e:
        print(f"   ⚠️  Stripe connection test failed: {e}")
        print("   This might be normal if you're using test keys")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Test existing configuration
        if not os.path.exists('.env'):
            print("❌ No .env file found. Run without --test to create one.")
            return
        
        print("🧪 Testing existing Stripe configuration...")
        os.system('python test_stripe.py')
    else:
        # Create new configuration
        create_stripe_env()


if __name__ == "__main__":
    main()
