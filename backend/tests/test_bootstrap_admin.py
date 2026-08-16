"""Production bootstrap must create a login-compatible admin on every startup."""

import pytest
from fastapi.testclient import TestClient


def test_bootstrap_rejects_email_that_login_schema_cannot_accept(client, monkeypatch):
    from app.db.database import SessionLocal
    from seed import seed_admin_from_environment

    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "admin@enterprise.local")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "BootstrapAdmin1!")
    db = SessionLocal()
    try:
        with pytest.raises(RuntimeError, match="valid email"):
            seed_admin_from_environment(db)
    finally:
        db.close()


def test_application_lifespan_runs_idempotent_admin_bootstrap(monkeypatch):
    from app import main as main_module

    calls = []
    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(
        main_module,
        "ensure_bootstrap_admin",
        lambda: calls.append("called"),
        raising=False,
    )
    monkeypatch.setattr(main_module.settings, "app_environment", "test")

    with TestClient(main_module.app):
        pass

    assert calls == ["called"]
