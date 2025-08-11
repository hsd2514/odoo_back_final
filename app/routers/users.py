from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.user import (
    UserCreate, UserLogin, UserRead, UserResponse,
    ForgotPasswordRequest, ResetPasswordRequest, PasswordResetResponse
)
from ..services.user_service import create_user, get_user_by_email, verify_password, update_user_password
from ..utils.jwt import create_access_token, create_password_reset_token, verify_password_reset_token
from ..utils.email import email_service


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", 
             response_model=UserResponse, 
             status_code=status.HTTP_201_CREATED,
             summary="Register a new user",
             description="Create a new user account with email, password, full name, and phone number")
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.
    
    This endpoint creates a new user account with the provided information.
    The password is hashed before storing in the database for security.
    A JWT access token is generated and returned upon successful registration.
    
    Args:
        user_data (UserCreate): User registration data containing:
            - email (str): User's email address (must be unique)
            - password (str): User's password (will be hashed)
            - full_name (str): User's full name
            - phone (str): User's phone number
        db (Session): Database session dependency
    
    Returns:
        UserResponse: Object containing:
            - message (str): Success message
            - user_id (int): ID of the created user
            - email (str): User's email address
            - full_name (str): User's full name
            - access_token (str): JWT token for authentication
            - token_type (str): Token type (always "bearer")
    
    Raises:
        HTTPException (400): If email is already registered
        HTTPException (422): If request data validation fails
    
    Example:
        POST /users/register
        {
            "email": "user@example.com",
            "password": "securepassword123",
            "full_name": "John Doe",
            "phone": "+1234567890"
        }
    """
    # Check if user already exists
    existing_user = get_user_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered. Please use a different email or login instead."
        )
    
    # Create new user
    new_user = create_user(
        db=db,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        phone=user_data.phone
    )
    
    # Create access token
    access_token = create_access_token(subject=new_user.id)
    
    return UserResponse(
        message="User registered successfully",
        user_id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        access_token=access_token,
        token_type="bearer"
    )


@router.post("/login",
             response_model=UserResponse,
             status_code=status.HTTP_200_OK,
             summary="User login",
             description="Authenticate user with email and password")
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and generate access token.
    
    This endpoint verifies user credentials and returns a JWT access token
    upon successful authentication. The password is verified against the
    hashed password stored in the database.
    
    Args:
        user_credentials (UserLogin): User login credentials containing:
            - email (str): User's email address
            - password (str): User's password (will be verified)
        db (Session): Database session dependency
    
    Returns:
        UserResponse: Object containing:
            - message (str): Success message
            - user_id (int): ID of the authenticated user
            - email (str): User's email address
            - full_name (str): User's full name
            - access_token (str): JWT token for authentication
            - token_type (str): Token type (always "bearer")
    
    Raises:
        HTTPException (404): If user with provided email is not found
        HTTPException (401): If password is incorrect
        HTTPException (422): If request data validation fails
    
    Example:
        POST /users/login
        {
            "email": "user@example.com",
            "password": "securepassword123"
        }
    """
    # Get user by email
    user = get_user_by_email(db, email=user_credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please check your email or register for a new account."
        )
    
    # Verify password
    if not verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password. Please check your password or use 'Forgot password' option."
        )
    
    # Create access token
    access_token = create_access_token(subject=user.id)
    
    return UserResponse(
        message="Login successful",
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        access_token=access_token,
        token_type="bearer"
    )


@router.post("/forgot-password",
             response_model=PasswordResetResponse,
             status_code=status.HTTP_200_OK,
             summary="Request password reset",
             description="Send password reset email to user's registered email address")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request password reset email.
    
    This endpoint accepts an email address and sends a password reset link
    to that email if the user exists in the system. For security reasons,
    it returns success even if the email doesn't exist in the database.
    
    Args:
        request (ForgotPasswordRequest): Contains the email address
        
    Returns:
        PasswordResetResponse: Success message
        
    Example:
        POST /users/forgot-password
        {
            "email": "user@example.com"
        }
    """
    # Check if user exists
    user = get_user_by_email(db, email=request.email)
    
    if user:
        # Generate password reset token
        reset_token = create_password_reset_token(request.email)
        
        # Send email (in production, you might want to queue this)
        email_sent = email_service.send_password_reset_email(
            email=request.email,
            reset_token=reset_token,
            user_name=user.full_name or ""
        )
        
        if not email_sent:
            # Log the error but don't expose it to the user for security
            print(f"Failed to send password reset email to {request.email}")
    
    # Always return success for security (don't reveal if email exists)
    return PasswordResetResponse(
        message="If the email address is registered with us, you will receive a password reset link shortly.",
        success=True
    )


@router.post("/reset-password",
             response_model=PasswordResetResponse,
             status_code=status.HTTP_200_OK,
             summary="Reset password with token",
             description="Reset user password using the token received via email")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using reset token.
    
    This endpoint accepts a password reset token (received via email) and
    a new password to update the user's password.
    
    Args:
        request (ResetPasswordRequest): Contains token and new password
        
    Returns:
        PasswordResetResponse: Success or error message
        
    Raises:
        HTTPException: If token is invalid or expired
        
    Example:
        POST /users/reset-password
        {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "new_password": "newsecurepassword123",
            "confirm_password": "newsecurepassword123"
        }
    """
    # Verify the reset token
    email = verify_password_reset_token(request.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token. Please request a new password reset."
        )
    
    # Get user by email
    user = get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. The account may have been deleted."
        )
    
    # Update user password
    success = update_user_password(db, user_id=user.id, new_password=request.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password. Please try again."
        )
    
    return PasswordResetResponse(
        message="Password reset successful. You can now login with your new password.",
        success=True
    )




