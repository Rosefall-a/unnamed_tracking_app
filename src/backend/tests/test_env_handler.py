from cryptography.fernet import Fernet

from src.core.env_handler import EnvConfigHandler
from src.core.fernet_key import persistent_fernet_key


import pytest


@pytest.fixture(autouse=True)
def isolated_app_data(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SECRET_KEY", raising=False)


def test_default_database_components_are_available():
    handler = EnvConfigHandler({"POSTGRES_PASSWORD": "secret"})
    values = handler.resolved()
    assert values["POSTGRES_USER"] == "archive"
    assert values["POSTGRES_DB"] == "archive"


def test_partial_database_configuration_is_unrecoverable():
    handler = EnvConfigHandler({"POSTGRES_USER": "archive"})
    issue = next(issue for issue in handler.validate() if issue.name == "database")
    assert issue.severity == "error"
    assert issue.recoverable is False


def test_partial_primary_user_configuration_is_unrecoverable():
    handler = EnvConfigHandler(
        {
            "PRIMARY_USER_USERNAME": "admin",
            "PRIMARY_USER_EMAIL": "admin@example.com",
        }
    )
    issue = next(issue for issue in handler.validate() if issue.name == "primary_user")
    assert issue.severity == "error"
    assert issue.recoverable is False


def test_oidc_missing_recommended_scope_is_warning():
    handler = EnvConfigHandler(
        {
            "OIDC_ISSUER_URL": "https://login.example.test",
            "OIDC_CLIENT_ID": "client",
            "OIDC_CLIENT_SECRET": "secret",
            "OIDC_SCOPES": "openid",
        }
    )
    issue = next(issue for issue in handler.validate() if issue.name == "oidc" and issue.severity == "warning")
    assert "profile" in issue.message
    assert "email" in issue.message


def test_development_mode_bootstraps_initial_admin_values():
    handler = EnvConfigHandler({"startup_mode": "development"})
    admin = handler.bootstrap_primary_user()
    assert admin == {
        "username": "admin",
        "email": "admin@localhost",
        "password": "Admin123!",
    }


def test_fernet_key_is_generated_and_persisted(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SECRET_KEY", raising=False)

    key = persistent_fernet_key()

    assert Fernet(key.encode())
    assert (tmp_path / "config" / "fernet.key").read_text(encoding="utf-8").strip() == key
    assert (tmp_path / "config" / "fernet.key.1").read_text(encoding="utf-8").strip() == key
    assert (tmp_path / "config" / "fernet.key.2").read_text(encoding="utf-8").strip() == key
