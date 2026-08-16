"""Password hashing, password policy, and JWT security primitives."""
import hashlib
import re
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings


settings = get_settings()
JWT_ISSUER = "enterprise-knowledge-assistant"

PASSWORD_RULES = {
    "min_length": lambda password: len(password) >= 8,
    "max_length": lambda password: len(password) <= 128,
    "uppercase": lambda password: bool(re.search(r"[A-Z]", password)),
    "lowercase": lambda password: bool(re.search(r"[a-z]", password)),
    "number": lambda password: bool(re.search(r"\d", password)),
    "special": lambda password: bool(re.search(r"[^A-Za-z0-9]", password)),
}


def password_requirements_report(password: str) -> dict[str, bool]:
    """Return the individual password-policy checks without exposing the password."""
    return {name: check(password) for name, check in PASSWORD_RULES.items()}


def is_password_strong(password: str) -> bool:
    return all(password_requirements_report(password).values())


def _bcrypt_input(password: str) -> bytes:
    """Prepare bcrypt input while retaining direct bcrypt primitives.

    bcrypt implementations commonly cap input at 72 bytes. Hashing longer
    valid policy inputs with a fixed-size SHA-256 digest keeps the configured
    128-character maximum usable without truncating a password silently.
    Normal-sized passwords are passed to bcrypt unchanged.
    """
    password_bytes = password.encode("utf-8")
    return password_bytes if len(password_bytes) <= 72 else hashlib.sha256(password_bytes).digest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_bcrypt_input(password), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_bcrypt_input(plain), hashed.encode("ascii"))
    except (TypeError, ValueError, UnicodeEncodeError):
        return False


def create_access_token(user_id: str, role: str | None = None) -> str:
    """Issue a token whose identity is the user id; role is deliberately not embedded.

    ``role`` remains an optional compatibility argument for existing callers,
    but authorization always reloads the role from the database.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        "iss": JWT_ISSUER,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Decode only JWTs with required, correctly typed claims and our issuer."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=JWT_ISSUER,
            options={
                "require_sub": True,
                "require_exp": True,
                "require_iat": True,
                "require_iss": True,
            },
        )
    except (JWTError, TypeError, ValueError):
        return None

    if payload.get("iss") != JWT_ISSUER or not isinstance(payload.get("sub"), str):
        return None
    if not payload["sub"].strip():
        return None
    return payload
