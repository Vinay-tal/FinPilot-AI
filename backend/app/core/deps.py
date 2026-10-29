from typing import Generator, Optional
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedException
from app.models.user import User

security_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    db: Session = Depends(get_db),
    token_auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> User:
    """Validate JWT access token and return authenticated User record."""
    if not token_auth:
        raise UnauthorizedException("Authentication token required.")
    
    token = token_auth.credentials
    try:
        payload = decode_access_token(token)
        user_id_str: Optional[str] = payload.get("sub")
        if not user_id_str:
            raise UnauthorizedException("Invalid token payload: missing subject identifier.")
        user_id = uuid.UUID(user_id_str)
    except Exception as exc:
        raise UnauthorizedException(f"Invalid or expired token: {str(exc)}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UnauthorizedException("User associated with this token no longer exists.")
    if not user.is_active:
        raise UnauthorizedException("User account is deactivated.")

    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency verifying the user is active."""
    return current_user
