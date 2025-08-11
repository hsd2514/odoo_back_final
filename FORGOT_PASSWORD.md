# Forgot Password Feature Documentation

## Overview

The forgot password feature allows users to reset their passwords by receiving a secure reset link via email. This implementation follows security best practices and provides a smooth user experience.

## How It Works

1. **Request Password Reset**: User provides their email address
2. **Email Sent**: System sends a password reset email with a secure token
3. **Reset Password**: User clicks the link and provides a new password
4. **Password Updated**: System validates the token and updates the password

## API Endpoints

### 1. Request Password Reset

**POST** `/users/forgot-password`

Request a password reset email for the given email address.

#### Request Body
```json
{
    "email": "user@example.com"
}
```

#### Response
```json
{
    "message": "If the email address is registered with us, you will receive a password reset link shortly.",
    "success": true
}
```

#### Security Notes
- Returns success even if email doesn't exist (prevents email enumeration)
- Rate limiting should be implemented in production
- Token expires in 15 minutes

### 2. Reset Password

**POST** `/users/reset-password`

Reset password using the token received via email.

#### Request Body
```json
{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "new_password": "newsecurepassword123",
    "confirm_password": "newsecurepassword123"
}
```

#### Response
```json
{
    "message": "Password reset successful. You can now login with your new password.",
    "success": true
}
```

#### Error Responses
- `400`: Invalid or expired token
- `404`: User not found
- `500`: Internal server error

## Email Configuration

### Environment Variables

Add these to your `.env` file:

```env
# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_FROM_NAME=Odoo Rental System

# Password Reset Configuration
PASSWORD_RESET_EXPIRE_MINUTES=15
```

### Gmail Setup

For Gmail, you need to:
1. Enable 2-factor authentication
2. Generate an app password
3. Use the app password in `SMTP_PASSWORD`

### Other Email Providers

#### Outlook/Hotmail
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
```

#### Yahoo
```env
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
```

#### Custom SMTP
```env
SMTP_SERVER=your-smtp-server.com
SMTP_PORT=587  # or 465 for SSL
```

## Security Features

### Token Security
- **Short Expiration**: Tokens expire in 15 minutes
- **Single Use**: Tokens should be invalidated after use (future enhancement)
- **Type Verification**: Tokens include type verification to prevent misuse
- **Cryptographic Signing**: Tokens are cryptographically signed

### Email Security
- **No Email Enumeration**: Same response regardless of email existence
- **HTML + Text**: Emails include both HTML and plain text versions
- **Clear Instructions**: Emails include security warnings and expiration info

### Password Security
- **Validation**: New passwords must meet minimum requirements
- **Confirmation**: Password confirmation prevents typos
- **Secure Hashing**: Passwords are hashed using bcrypt

## Email Template

The system sends a professionally formatted email with:
- Clear subject line
- Professional branding
- Secure reset link
- Expiration warning
- Security instructions
- Plain text fallback

## Testing

### Manual Testing

1. Start the server:
```bash
uvicorn app.main:app --reload
```

2. Go to http://localhost:8000/docs

3. Test the `/users/forgot-password` endpoint

4. Check the server logs for the generated token

5. Test the `/users/reset-password` endpoint with the token

### Automated Testing

Run the test script:
```bash
python test_forgot_password.py
```

## Frontend Integration

### Forgot Password Form
```javascript
const forgotPassword = async (email) => {
    const response = await fetch('/users/forgot-password', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email })
    });
    
    const data = await response.json();
    // Always show success message for security
    showMessage(data.message);
};
```

### Reset Password Form
```javascript
const resetPassword = async (token, newPassword, confirmPassword) => {
    const response = await fetch('/users/reset-password', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            token,
            new_password: newPassword,
            confirm_password: confirmPassword
        })
    });
    
    if (response.ok) {
        const data = await response.json();
        showSuccessMessage(data.message);
        redirectToLogin();
    } else {
        const error = await response.json();
        showErrorMessage(error.detail);
    }
};
```

## Production Considerations

### Email Deliverability
- Use a dedicated email service (SendGrid, AWS SES, etc.)
- Set up SPF, DKIM, and DMARC records
- Monitor bounce rates and delivery metrics

### Rate Limiting
- Implement rate limiting on forgot password endpoint
- Limit to 3-5 requests per hour per IP/email

### Monitoring
- Log failed email sends
- Monitor token usage patterns
- Alert on suspicious activity

### Database Considerations
- Consider storing password reset tokens in database for invalidation
- Add audit trail for password changes
- Implement password history to prevent reuse

## Error Handling

The system handles various error scenarios:
- Invalid email format
- Non-existent users
- Expired tokens
- Email delivery failures
- Database errors

All errors are logged for debugging while maintaining user privacy.

## Future Enhancements

1. **Token Invalidation**: Store tokens in database for single-use
2. **Account Lockout**: Temporary lockout after multiple reset attempts
3. **Email Templates**: Customizable email templates
4. **Multi-language**: Support for multiple languages
5. **SMS Reset**: Alternative reset via SMS
6. **Security Questions**: Additional verification methods
