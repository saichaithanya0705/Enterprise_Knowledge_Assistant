"""Regression coverage for upgrading the pre-authentication SQLite schema."""
import sqlite3


def test_init_db_adds_identity_columns_without_losing_existing_rows(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(
            """
            CREATE TABLE conversations (
                id VARCHAR(36) PRIMARY KEY,
                title VARCHAR(255),
                created_at DATETIME
            );
            CREATE TABLE documents (
                id VARCHAR(36) PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                file_type VARCHAR(20) NOT NULL,
                category VARCHAR(100),
                status VARCHAR(20),
                char_count INTEGER,
                chunk_count INTEGER,
                error_message TEXT,
                created_at DATETIME
            );
            INSERT INTO conversations (id, title, created_at)
            VALUES ('legacy-conversation', 'Preserved history', CURRENT_TIMESTAMP);
            """
        )
        connection.commit()
    finally:
        connection.close()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    from app.core.config import get_settings
    import app.db.database as database

    get_settings.cache_clear()
    database.reset_for_tests()
    try:
        database.init_db()
        connection = sqlite3.connect(database_path)
        try:
            conversation_columns = {
                row[1] for row in connection.execute("PRAGMA table_info('conversations')")
            }
            document_columns = {
                row[1] for row in connection.execute("PRAGMA table_info('documents')")
            }
            preserved = connection.execute(
                "SELECT title, user_id, is_deleted FROM conversations WHERE id = ?",
                ("legacy-conversation",),
            ).fetchone()
        finally:
            connection.close()
    finally:
        database.reset_for_tests()
        get_settings.cache_clear()

    assert {"user_id", "is_deleted", "deleted_at", "deleted_by"} <= conversation_columns
    assert "uploaded_by" in document_columns
    assert preserved == ("Preserved history", None, 0)
