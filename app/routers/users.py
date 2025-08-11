from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.user import UserCreate, UserLogin, UserRead, UserResponse
from ..services.user_service import create_user, get_user_by_email, verify_password
from ..utils.jwt import create_access_token


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




