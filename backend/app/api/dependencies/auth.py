"""FastAPI dependencies for JWT authentication and database-backed RBAC."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.user import User
from app.repositories import user_repo


_bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Your session is invalid or has expired. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve identity exclusively from a validated bearer JWT subject."""
    if credentials is None:
        raise _unauthorized()

    payload = decode_access_token(credentials.credentials)
    subject = payload.get("sub") if payload else None
    if not isinstance(subject, str) or not subject.strip():
        raise _unauthorized()

    user = user_repo.get_by_id(db, subject)
    if user is None:
        raise _unauthorized()
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Authorize using the current database role, never a token role claim."""
    if user.role != "ADMIN":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required.")
    return user
