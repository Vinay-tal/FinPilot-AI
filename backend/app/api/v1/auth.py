from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.deps import get_current_user
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from app.models.user import User
from app.services.auth_service import register_user, authenticate_user, get_demo_user

router = APIRouter(prefix="/auth", tags=["Authentication & User Management"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)) -> TokenResponse:
    """Register a new user account and obtain access token."""
    user, token = register_user(db, user_in)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )

@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate with email and password to receive access token."""
    user, token = authenticate_user(db, credentials)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )

@router.post("/demo-login", response_model=TokenResponse)
def demo_login(db: Session = Depends(get_db)) -> TokenResponse:
    """
    Instant 1-click evaluation login as the Rahul Sharma demo persona.
    Automatically seeds 12 months of realistic Indian financial data if not already present.
    """
    user, token = get_demo_user(db)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Fetch profile information for authenticated user."""
    return UserResponse.model_validate(current_user)

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(current_user: User = Depends(get_current_user)) -> dict:
    """Explicitly terminate authenticated session and acknowledge client token revocation."""
    return {
        "status": "success",
        "message": f"User {current_user.email} successfully logged out. Session terminated."
    }
