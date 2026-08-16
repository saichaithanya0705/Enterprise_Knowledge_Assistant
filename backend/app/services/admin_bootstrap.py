"""Idempotent production administrator bootstrap."""

import os

from pydantic import ValidationError

from app.core.security import hash_password, is_password_strong, verify_password
from app.db.database import SessionLocal
from app.repositories import user_repo
from app.schemas.auth import LoginRequest


def seed_admin_from_environment(db):
    """Create the configured admin after validating login-compatible credentials."""
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    name = os.getenv("BOOTSTRAP_ADMIN_NAME", "Administrator").strip() or "Administrator"
    if not email and not password:
        return None
    if not email or not password:
        raise RuntimeError("Set both BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD.")
    if not is_password_strong(password):
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD does not meet the password policy.")
    try:
        credentials = LoginRequest(email=email, password=password)
    except ValidationError as exc:
        raise RuntimeError("BOOTSTRAP_ADMIN_EMAIL must be a valid email accepted by login.") from exc
    normalized_email = str(credentials.email)
    existing = user_repo.get_by_email(db, normalized_email)
    if existing:
        password_hash = None
        if not verify_password(password, existing.password_hash):
            password_hash = hash_password(password)
        return user_repo.synchronize_bootstrap_admin(
            db,
            existing,
            name=name,
            password_hash=password_hash,
        )
    return user_repo.create_user(
        db,
        name,
        normalized_email,
        hash_password(password),
        role="ADMIN",
    )


def ensure_bootstrap_admin() -> None:
    """Ensure the configured admin exists after each process startup."""
    db = SessionLocal()
    try:
        seed_admin_from_environment(db)
    finally:
        db.close()
