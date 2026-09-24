from cryptography.fernet import Fernet
import pytest

from src.core.env_handler import EnvConfigHandler
from src.core.fernet_key import persistent_fernet_key


@pytest.fixture(autouse=True)
def isolated_app_data(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SECRET_KEY", raising=False)


def test_database_components_are_resolved():
    handler = EnvConfigHandler({
        "POSTGRES_USER": "archive",
        "POSTGRES_PASSWORD": "secret",
        "POSTGRES_DB": "archive",
    })
    values = handler.resolved()
    assert values["POSTGRES_USER"] == "archive"
    assert values["POSTGRES_DB"] == "archive"


def test_partial_database_configuration_is_unrecoverable():
    handler = EnvConfigHandler({"POSTGRES_USER": "archive"})
    issue = next(issue for issue in handler.validate() if issue.name == "database")
    assert issue.severity == "error"
    assert issue.recoverable is False


def test_partial_primary_user_configuration_is_unrecoverable():
    handler = EnvConfigHandler({
        "PRIMARY_USER_USERNAME": "admin",
        "PRIMARY_USER_EMAIL": "admin@example.com",
    })
    issue = next(issue for issue in handler.validate() if issue.name == "primary_user")
    assert issue.severity == "error"
    assert issue.recoverable is False


def test_oidc_missing_recommended_scope_is_warning():
    handler = EnvConfigHandler({
        "OIDC_ISSUER_URL": "https://login.example.test",
        "OIDC_CLIENT_ID": "client",
        "OIDC_CLIENT_SECRET": "secret",
        "OIDC_SCOPES": "openid",
    })
    issue = next(issue for issue in handler.validate() if issue.name == "oidc" and issue.severity == "warning")
    assert "profile" in issue.message
    assert "email" in issue.message


def test_oidc_can_be_disabled_with_partial_credentials():
    handler = EnvConfigHandler({
        "OIDC_ENABLED": "false",
        "OIDC_ISSUER_URL": "https://login.example.test",
    })
    assert handler.oidc_enabled() is False
    assert not any(issue.name == "oidc" and issue.severity == "error" for issue in handler.validate())


def test_setup_schema_marks_environment_fields_locked_and_partial():
    handler = EnvConfigHandler({
        "POSTGRES_USER": "archive",
        "POSTGRES_PASSWORD": "secret",
        "POSTGRES_DB": "archive",
        "OIDC_ISSUER_URL": "https://login.example.test",
        "OIDC_CLIENT_ID": "client",
    })
    sections = {section["id"]: section for section in handler.setup_schema()}
    assert sections["database"]["status"] == "completed_by_env"
    assert sections["oidc"]["status"] == "partial"

    issuer = next(field for field in sections["oidc"]["fields"] if field["name"] == "OIDC_ISSUER_URL")
    secret = next(field for field in sections["oidc"]["fields"] if field["name"] == "OIDC_CLIENT_SECRET")
    assert issuer["locked"] is True
    assert issuer["value"] == "https://login.example.test"
    assert secret["locked"] is False
    assert secret["value"] is None


def test_fernet_key_is_generated_and_persisted(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SECRET_KEY", raising=False)

    key = persistent_fernet_key()

    assert Fernet(key.encode())
    assert (tmp_path / "config" / "fernet.key").read_text(encoding="utf-8").strip() == key
    assert (tmp_path / "config" / "fernet.key.1").read_text(encoding="utf-8").strip() == key
    assert (tmp_path / "config" / "fernet.key.2").read_text(encoding="utf-8").strip() == key


def test_legacy_database_url_is_only_a_warning():
    handler = EnvConfigHandler({
        "DATABASE_URL": "postgresql+psycopg://archive:secret@db:5432/archive"
    })
    issue = next(issue for issue in handler.validate() if issue.name == "database")
    assert issue.severity == "warning"


def test_env_only_frontend_value_is_not_exposed_to_setup():
    handler = EnvConfigHandler({"VITE_USE_MOCK_DATA": "true"})
    assert all(
        field["name"] != "VITE_USE_MOCK_DATA"
        for section in handler.setup_schema()
        for field in section["fields"]
    )
