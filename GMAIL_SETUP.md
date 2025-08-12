# Gmail SMTP Setup Guide for Forgot Password Feature

## Prerequisites

1. A Gmail account
2. 2-Factor Authentication enabled on your Gmail account

## Step-by-Step Gmail Configuration

### Step 1: Enable 2-Factor Authentication

1. Go to your [Google Account settings](https://myaccount.google.com)
2. Click on "Security" in the left sidebar
3. Under "Signing in to Google", click on "2-Step Verification"
4. Follow the setup process to enable 2FA

### Step 2: Generate App Password

1. Go to [Google Account settings](https://myaccount.google.com)
2. Click on "Security" in the left sidebar
3. Under "Signing in to Google", click on "App passwords"
4. You may need to sign in again
5. Click "Select app" dropdown and choose "Mail"
6. Click "Select device" dropdown and choose "Other (custom name)"
7. Enter "Odoo Rental System" as the custom name
8. Click "Generate"
9. **Copy the 16-character app password** (it will look like: `abcd efgh ijkl mnop`)

### Step 3: Configure Your .env File

Create a `.env` file in your project root with the following:

```env
# Database Configuration
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/odoo_final

# Security Configuration
SECRET_KEY=your-super-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_ALGORITHM=HS256
PASSWORD_RESET_EXPIRE_MINUTES=15

# Gmail SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
GMAIL_USERNAME=your-actual-email@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
EMAIL_FROM=your-actual-email@gmail.com
EMAIL_FROM_NAME=Odoo Rental System

# Application Configuration
APP_NAME=Odoo Rental Management System
```

**Important:** Replace the placeholder values:
- `your-actual-email@gmail.com` → Your actual Gmail address
- `abcd efgh ijkl mnop` → The 16-character app password from Step 2

### Step 4: Test the Configuration

Run the test script to verify everything works:

```bash
python test_forgot_password.py
```

You should see output like:
```
✅ Email configuration looks good
✅ Token generation and verification working correctly
```

## Security Notes

### App Passwords vs Account Password
- **Never use your actual Gmail password** in the application
- **Always use App Passwords** for third-party applications
- App passwords are safer because they can be revoked individually

### Gmail Security Features
- Gmail automatically detects and blocks suspicious login attempts
- App passwords are automatically revoked if 2FA is disabled
- You can revoke app passwords anytime from your Google Account settings

## Common Issues and Solutions

### Issue 1: "Username and Password not accepted"
**Solution:** 
- Make sure you're using the App Password, not your regular Gmail password
- Ensure 2FA is enabled on your Google account
- Double-check the email address spelling

### Issue 2: "SMTPAuthenticationError"
**Solution:**
- Verify the App Password is correct (16 characters with spaces)
- Try generating a new App Password
- Make sure "Less secure app access" is not interfering (it shouldn't with App Passwords)

### Issue 3: "Connection refused" or "Timeout"
**Solution:**
- Check your internet connection
- Verify firewall isn't blocking port 587
- Some networks block SMTP ports - try a different network

### Issue 4: App Password option not available
**Solution:**
- Ensure 2-Factor Authentication is fully enabled
- Wait a few minutes after enabling 2FA
- Make sure your Google account is not a G Suite account with restrictions

## Testing Email Delivery

### Test Script Usage
```bash
# Test configuration only
python test_forgot_password.py

# Test with actual email sending (when server is running)
# 1. Start server: uvicorn app.main:app --reload
# 2. Test via API documentation: http://localhost:8000/docs
# 3. Use the /users/forgot-password endpoint
```

### Manual Testing Steps
1. Start your server: `uvicorn app.main:app --reload`
2. Go to http://localhost:8000/docs
3. Find the "POST /users/forgot-password" endpoint
4. Click "Try it out"
5. Enter your test email address
6. Click "Execute"
7. Check your email inbox for the password reset email

## Email Delivery Tips

### Avoid Spam Folder
- Use a clear, professional "From" name
- Don't use suspicious keywords in subject lines
- Gmail's spam filters are usually good with App Passwords

### Improve Deliverability
- Send from your actual domain when possible
- Set up SPF records if using a custom domain
- Keep email content professional and well-formatted

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `GMAIL_USERNAME` | Your Gmail address | `john.doe@gmail.com` |
| `GMAIL_APP_PASSWORD` | 16-character app password | `abcd efgh ijkl mnop` |
| `EMAIL_FROM` | Sender email (usually same as GMAIL_USERNAME) | `john.doe@gmail.com` |
| `EMAIL_FROM_NAME` | Display name for sender | `Odoo Rental System` |
| `SMTP_SERVER` | Gmail SMTP server | `smtp.gmail.com` |
| `SMTP_PORT` | Gmail SMTP port | `587` |

## Production Considerations

### For Production Use
1. **Use a dedicated email account** for your application
2. **Monitor sending limits** (Gmail has daily sending limits)
3. **Consider dedicated email services** like SendGrid or AWS SES for high volume
4. **Set up proper DNS records** (SPF, DKIM, DMARC) if using custom domains

### Gmail Sending Limits
- **New accounts**: ~100 emails/day
- **Established accounts**: ~500 emails/day
- **G Suite accounts**: Higher limits available

## Troubleshooting Commands

```bash
# Test SMTP connection
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'your-app-password')
print('✅ Gmail SMTP connection successful!')
server.quit()
"

# Test configuration loading
python -c "
from app.config import get_settings
settings = get_settings()
print(f'SMTP Server: {settings.smtp_server}')
print(f'SMTP Port: {settings.smtp_port}')
print(f'Username: {settings.smtp_username}')
print(f'From Email: {settings.email_from}')
"
```

## Need Help?

If you encounter issues:
1. Double-check all steps in this guide
2. Verify your .env file syntax
3. Test with a simple Python SMTP script first
4. Check Gmail's App Password documentation
5. Ensure no typos in email addresses or passwords

Your Gmail SMTP setup is now ready for the forgot password feature! 🎉
