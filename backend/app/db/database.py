"""SQLAlchemy engine and session management."""
from sqlalchemy import create_engine, event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


# Lazily constructed so tests can point at a fresh DATABASE_URL per test by
# clearing the settings cache and calling reset_for_tests() first.
_engine = None
_SessionLocal = None
_FEEDBACK_UNIQUE_INDEX = "uq_feedback_message_id"


def _ensure_initialized():
    global _engine, _SessionLocal
    if _engine is not None:
        return
    settings = get_settings()
    connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}
    _engine = create_engine(settings.database_url, connect_args=connect_args)
    if _engine.dialect.name == "sqlite":
        event.listen(_engine, "connect", _enable_sqlite_foreign_keys)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Enable SQLite referential-integrity enforcement for every connection."""
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


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
    if _engine.dialect.name == "sqlite":
        _migrate_sqlite_feedback_uniqueness()


def _migrate_sqlite_feedback_uniqueness():
    """Install the ORM feedback uniqueness rule on existing SQLite databases."""
    with _engine.begin() as connection:
        if _sqlite_feedback_has_message_unique_index(connection):
            return

        duplicate = connection.exec_driver_sql(
            """
            SELECT message_id, COUNT(*) AS row_count
            FROM feedback
            WHERE message_id IS NOT NULL
            GROUP BY message_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        ).first()
        if duplicate is not None:
            raise RuntimeError(
                "SQLite startup migration cannot create duplicate feedback message_id "
                f"constraint: message_id {duplicate[0]!r} has {duplicate[1]} rows. "
                "Resolve the duplicate feedback rows manually, then restart; rows were preserved."
            )

        try:
            connection.exec_driver_sql(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {_FEEDBACK_UNIQUE_INDEX} "
                "ON feedback (message_id)"
            )
        except SQLAlchemyError as error:
            if _sqlite_feedback_has_message_unique_index(connection):
                return
            raise _feedback_migration_error(connection) from error

        if not _sqlite_feedback_has_message_unique_index(connection):
            raise _feedback_migration_error(connection)


def _feedback_migration_error(connection):
    duplicate = connection.exec_driver_sql(
        """
        SELECT message_id, COUNT(*) AS row_count
        FROM feedback
        WHERE message_id IS NOT NULL
        GROUP BY message_id
        HAVING COUNT(*) > 1
        LIMIT 1
        """
    ).first()
    if duplicate is not None:
        return RuntimeError(
            "SQLite startup migration cannot create duplicate feedback message_id "
            f"constraint: message_id {duplicate[0]!r} has {duplicate[1]} rows. "
            "Resolve the duplicate feedback rows manually, then restart; rows were preserved."
        )
    return RuntimeError(
        "SQLite startup migration could not verify the feedback message_id uniqueness "
        "constraint. Restart after resolving the database condition; rows were preserved."
    )


def _sqlite_feedback_has_message_unique_index(connection):
    """Return whether feedback.message_id is already covered by a unique index."""
    for index in connection.exec_driver_sql("PRAGMA index_list('feedback')").fetchall():
        index_name = index[1]
        is_unique = index[2]
        if not is_unique:
            continue
        escaped_name = index_name.replace("'", "''")
        columns = [
            column[2]
            for column in connection.exec_driver_sql(
                f"PRAGMA index_info('{escaped_name}')"
            ).fetchall()
        ]
        if columns == ["message_id"]:
            return True
    return False


def reset_for_tests():
    """Drop the cached engine/session so the next call rebuilds against the current settings."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
