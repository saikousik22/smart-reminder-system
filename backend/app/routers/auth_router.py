"""
Authentication router: signup, login, and current-user endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas import UserSignup, UserLogin, UserResponse, TokenResponse, MessageResponse
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.rate_limit import login_rate_limit, signup_rate_limit

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: UserSignup, db: Session = Depends(get_db), _: None = Depends(signup_rate_limit)):
    """Register a new user account."""
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if username already exists
    existing_username = db.query(User).filter(User.username == payload.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    # Create user
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": f"User '{user.username}' created successfully"}


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, response: Response, db: Session = Depends(get_db), _: None = Depends(login_rate_limit)):
    """Authenticate and receive a JWT access token (also set as HttpOnly cookie)."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(data={"sub": user.id})
    # CSRF protection: samesite="strict" blocks the cookie from being sent in
    # any cross-site request (forged form POST, AJAX from attacker domain).
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="strict",
        max_age=settings.JWT_EXPIRY_HOURS * 3600,
        secure=settings.COOKIE_SECURE,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    """Clear the authentication cookie."""
    response.delete_cookie("access_token", samesite="strict")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return current_user
