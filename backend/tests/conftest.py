"""Shared pytest fixtures: an isolated SQLite DB + Chroma dir per test."""
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def client(monkeypatch):
    tmp_dir = tempfile.mkdtemp()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_dir}/test.db")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", f"{tmp_dir}/chroma")

    from app.core.config import get_settings
    get_settings.cache_clear()

    import app.db.database as database_module
    import app.rag.vector_store as vector_store_module
    database_module.reset_for_tests()
    vector_store_module.reset_for_tests()

    from app.main import app
    with TestClient(app) as c:
        yield c

    database_module.reset_for_tests()
    vector_store_module.reset_for_tests()
    shutil.rmtree(tmp_dir, ignore_errors=True)
