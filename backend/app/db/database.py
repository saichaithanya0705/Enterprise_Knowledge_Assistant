"""SQLAlchemy engine and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


# Lazily constructed so tests can point at a fresh DATABASE_URL per test by
# clearing the settings cache and calling reset_for_tests() first.
_engine = None
_SessionLocal = None


def _ensure_initialized():
    global _engine, _SessionLocal
    if _engine is not None:
        return
    settings = get_settings()
    connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}
    _engine = create_engine(settings.database_url, connect_args=connect_args)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def SessionLocal():
    """Callable factory kept for scripts (seed.py) that want a session outside a request."""
    _ensure_initialized()
    return _SessionLocal()


def get_db():
    _ensure_initialized()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    _ensure_initialized()
    from app.models import document, conversation  # noqa: F401 - register models on Base.metadata
    Base.metadata.create_all(bind=_engine)


def reset_for_tests():
    """Drop the cached engine/session so the next call rebuilds against the current settings."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
