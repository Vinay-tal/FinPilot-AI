from typing import Tuple
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.config import settings

def register_user(db: Session, user_in: UserRegister) -> Tuple[User, str]:
    """Register a new user and generate access token."""
    existing = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing:
        raise ConflictException(
            f"An account with email '{user_in.email}' already exists.",
            details={"email": user_in.email}
        )

    user = User(
        email=user_in.email.lower(),
        password_hash=hash_password(user_in.password),
        full_name=user_in.full_name,
        currency=user_in.currency or "INR",
        is_active=True,
        is_demo=False,
    )
    db.add(user)
    db.flush()  # assign user.id

    token = create_access_token(user.id)
    return user, token

def authenticate_user(db: Session, credentials: UserLogin) -> Tuple[User, str]:
    """Verify credentials and issue access token."""
    user = db.query(User).filter(User.email == credentials.email.lower()).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise UnauthorizedException("Incorrect email or password.")
    if not user.is_active:
        raise UnauthorizedException("Account is currently disabled.")

    token = create_access_token(user.id)
    return user, token

def get_demo_user(db: Session) -> Tuple[User, str]:
    """Retrieve or trigger seeding for the Rahul Sharma demo persona and return token."""
    demo_user = db.query(User).filter(User.email == settings.DEMO_USER_EMAIL.lower()).first()
    if not demo_user:
        # Import lazily to avoid circular dependencies
        from app.db.seed_data import seed_demo_data
        demo_user = seed_demo_data(db)

    token = create_access_token(demo_user.id)
    return demo_user, token
