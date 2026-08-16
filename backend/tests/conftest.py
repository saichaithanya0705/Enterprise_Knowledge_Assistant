"""Shared pytest fixtures: an isolated SQLite DB + Chroma dir per test."""
import os
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient


# Test modules import application settings during collection, before fixtures
# run. Explicit process values take precedence over a developer's local .env
# and keep the default suite deterministic and offline. Provider-specific tests
# opt in by monkeypatching their module settings.
os.environ["KEY_GATEWAY_URL"] = ""
os.environ["KEY_GATEWAY_API_KEY"] = ""
os.environ["NVIDIA_API_KEY"] = ""
os.environ["JWT_SECRET_KEY"] = "test-secret-not-for-production"
os.environ["APP_ENVIRONMENT"] = "test"


@pytest.fixture(scope="function")
def client(monkeypatch):
    tmp_dir = tempfile.mkdtemp()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_dir}/test.db")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", f"{tmp_dir}/chroma")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-not-for-production")
    monkeypatch.setenv("APP_ENVIRONMENT", "test")

    from app.core.config import get_settings
    get_settings.cache_clear()

    import app.db.database as database_module
    import app.rag.vector_store as vector_store_module
    database_module.reset_for_tests()
    vector_store_module.reset_for_tests()

    from app.main import app
    with TestClient(app) as c:
        from app.core.security import create_access_token, hash_password
        from app.db.database import SessionLocal
        from app.repositories import user_repo

        db = SessionLocal()
        try:
            admin = user_repo.create_user(
                db,
                name="Legacy Test Admin",
                email="legacy-admin@example.com",
                password_hash=hash_password("LegacyAdmin1!"),
                role="ADMIN",
            )
            c.headers.update({"Authorization": f"Bearer {create_access_token(admin.id, admin.role)}"})
        finally:
            db.close()
        yield c

    database_module.reset_for_tests()
    vector_store_module.reset_for_tests()
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def anonymous_client(client):
    """A token-free client sharing the current test's isolated database."""
    from app.main import app

    with TestClient(app) as anonymous:
        yield anonymous


def _register(client, email, password="Testpass1!", name="Test User"):
    response = client.post(
        "/api/auth/register",
        json={
            "name": name,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


@pytest.fixture
def user_token(anonymous_client):
    return _register(anonymous_client, "member@example.com")


@pytest.fixture
def admin_token(anonymous_client):
    token = _register(anonymous_client, "admin-test@example.com")
    from app.db.database import SessionLocal
    from app.repositories import user_repo

    db = SessionLocal()
    try:
        user = user_repo.get_by_email(db, "admin-test@example.com")
        user_repo.set_role(db, user, "ADMIN")
    finally:
        db.close()
    response = anonymous_client.post(
        "/api/auth/login",
        json={"email": "admin-test@example.com", "password": "Testpass1!"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
