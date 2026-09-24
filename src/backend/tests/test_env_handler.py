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


def test_env_only_required_fields_block_setup_and_are_marked():
    handler = EnvConfigHandler({"POSTGRES_USER": "archive"})
    sections = {section["id"]: section for section in handler.setup_schema()}
    database = sections["database"]
    assert database["blocked"] is True
    assert database["status"] == "blocked_by_env"
    assert "POSTGRES_PASSWORD" in database["blocked_message"]
    password = next(field for field in database["fields"] if field["name"] == "POSTGRES_PASSWORD")
    assert password["env_only"] is True
    assert password["visible"] is False


def test_env_owned_non_secret_values_remain_visible_and_locked():
    handler = EnvConfigHandler({
        "POSTGRES_USER": "archive",
        "POSTGRES_PASSWORD": "secret",
        "POSTGRES_DB": "archive",
        "AUTH_COOKIE_SECURE": "true",
    })
    fields = {
        field["name"]: field
        for section in handler.setup_schema()
        for field in section["fields"]
    }
    assert fields["AUTH_COOKIE_SECURE"]["value"] is True
    assert fields["AUTH_COOKIE_SECURE"]["visible"] is True
    assert fields["AUTH_COOKIE_SECURE"]["locked"] is True


def test_deprecated_setting_exposes_replacement_message():
    handler = EnvConfigHandler({"DATABASE_URL": "postgresql+psycopg://archive:secret@db/archive"})
    field = next(
        field for section in handler.setup_schema() for field in section["fields"]
        if field["name"] == "DATABASE_URL"
    )
    assert field["deprecated_message"] == (
        "DATABASE_URL is deprecated; use POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB instead."
    )


def test_oidc_section_is_environment_configured_when_any_oidc_value_is_supplied():
    handler = EnvConfigHandler({"OIDC_ENABLED": "true"})
    section = next(section for section in handler.setup_schema() if section["id"] == "oidc")
    assert section["env_configured"] is True
