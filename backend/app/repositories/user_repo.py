"""Data access for users with rollback-safe persistence operations."""
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.user import User


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def get_by_email(db: Session, email: str) -> User | None:
    try:
        return db.query(User).filter(User.email == _normalize_email(email)).first()
    except SQLAlchemyError:
        db.rollback()
        raise


def get_by_id(db: Session, user_id: str) -> User | None:
    try:
        return db.query(User).filter(User.id == user_id).first()
    except SQLAlchemyError:
        db.rollback()
        raise


def create_user(db: Session, name: str, email: str, password_hash: str, role: str = "USER") -> User:
    user = User(name=name, email=_normalize_email(email), password_hash=password_hash, role=role)
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except SQLAlchemyError:
        db.rollback()
        raise


def list_users(db: Session) -> list[User]:
    try:
        return db.query(User).order_by(User.created_at.desc()).all()
    except SQLAlchemyError:
        db.rollback()
        raise


def count_active_admins(db: Session) -> int:
    try:
        return db.query(User).filter(User.role == "ADMIN", User.is_active.is_(True)).count()
    except SQLAlchemyError:
        db.rollback()
        raise


def set_last_login(db: Session, user: User) -> None:
    user.last_login_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def set_active(db: Session, user: User, is_active: bool) -> None:
    user.is_active = is_active
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def set_role(db: Session, user: User, role: str) -> None:
    user.role = role
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def update_profile(db: Session, user: User, name: str | None) -> User:
    if name is not None:
        user.name = name
    try:
        db.commit()
        db.refresh(user)
        return user
    except SQLAlchemyError:
        db.rollback()
        raise


def set_password(db: Session, user: User, password_hash: str) -> None:
    user.password_hash = password_hash
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
