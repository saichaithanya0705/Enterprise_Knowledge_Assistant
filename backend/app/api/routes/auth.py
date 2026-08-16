"""Authentication and account-management endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.security import (
    create_access_token,
    hash_password,
    is_password_strong,
    password_requirements_report,
    verify_password,
)
from app.db.database import get_db
from app.models.user import User
from app.repositories import audit_repo, user_repo
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    PasswordRequirementsOut,
    PasswordRequirementsRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserOut,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)
PASSWORD_ERROR = (
    "Password must be 8-128 characters and include an uppercase letter, "
    "a lowercase letter, a number, and a special character."
)


def _user_out(user: User) -> UserOut:
    return UserOut.model_validate(user)


def _persistence_failure(db: Session, action: str, error: Exception) -> HTTPException:
    db.rollback()
    logger.warning("Authentication persistence failed action=%s error_type=%s", action, type(error).__name__)
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Unable to complete the request.")


@router.post("/password-requirements", response_model=PasswordRequirementsOut)
def check_password_requirements(payload: PasswordRequirementsRequest):
    report = password_requirements_report(payload.password)
    return PasswordRequirementsOut(**report, overall_valid=all(report.values()))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if payload.password != payload.confirm_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passwords do not match.")
    if not is_password_strong(payload.password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, PASSWORD_ERROR)

    try:
        if user_repo.get_by_email(db, payload.email):
            raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")

        user = user_repo.create_user(
            db,
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role="USER",
        )
        audit_repo.log_action(db, user, "REGISTER", target_type="user", target_id=user.id)
        return TokenResponse(access_token=create_access_token(user.id), user=_user_out(user))
    except HTTPException:
        raise
    except IntegrityError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.") from error
    except SQLAlchemyError as error:
        raise _persistence_failure(db, "register", error) from error


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    try:
        user = user_repo.get_by_email(db, payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise invalid
        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated.")

        user_repo.set_last_login(db, user)
        audit_repo.log_action(db, user, "LOGIN", target_type="user", target_id=user.id)
        return TokenResponse(access_token=create_access_token(user.id), user=_user_out(user))
    except HTTPException:
        raise
    except SQLAlchemyError as error:
        raise _persistence_failure(db, "login", error) from error


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return _user_out(current_user)


def _update_profile(
    payload: UpdateProfileRequest,
    db: Session,
    current_user: User,
) -> UserOut:
    try:
        user = user_repo.update_profile(db, current_user, payload.name)
        audit_repo.log_action(db, user, "PROFILE_UPDATE", target_type="user", target_id=user.id)
        return _user_out(user)
    except SQLAlchemyError as error:
        raise _persistence_failure(db, "profile_update", error) from error


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _update_profile(payload, db, current_user)


@router.patch("/profile", response_model=UserOut)
def update_profile(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _update_profile(payload, db, current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect.")
    if payload.new_password != payload.confirm_new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "New passwords do not match.")
    if not is_password_strong(payload.new_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, PASSWORD_ERROR)

    try:
        user_repo.set_password(db, current_user, hash_password(payload.new_password))
        audit_repo.log_action(db, current_user, "PASSWORD_CHANGE", target_type="user", target_id=current_user.id)
    except SQLAlchemyError as error:
        raise _persistence_failure(db, "password_change", error) from error
