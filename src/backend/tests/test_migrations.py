from alembic.config import Config
from alembic.script import ScriptDirectory

from src.database.migrate import decide


def _script() -> ScriptDirectory:
    return ScriptDirectory.from_config(Config("alembic.ini"))


def test_history_is_a_single_line():
    script = _script()
    assert len(script.get_heads()) == 1
    assert len(script.get_bases()) == 1


def test_empty_database_is_built_from_the_migrations():
    assert decide(set(), {"a"}, has_tables=False).action == "fresh"


def test_known_version_is_a_normal_upgrade():
    assert decide({"a"}, {"a", "b"}, has_tables=True).action == "upgrade"


def test_unknown_or_missing_version_is_adopted_not_crashed_on():
    assert decide({"gone"}, {"a"}, has_tables=True).action == "adopt"
    assert decide(set(), {"a"}, has_tables=True).action == "adopt"


def test_a_key_saved_in_settings_wins_over_the_environment(monkeypatch):
    from types import SimpleNamespace

    from src.core import integrations
    from src.core.crypto import encrypt_secret

    monkeypatch.setitem(integrations._ENV, "tmdb_api_key", "from-env")
    monkeypatch.setitem(integrations._ENV, "omdb_api_key", "omdb-env")
    monkeypatch.setitem(integrations._ENV, "tvdb_api_key", None)
    row = SimpleNamespace(
        igdb_client_id=None,
        igdb_client_secret=None,
        tvdb_api_key=None,
        omdb_api_key=None,
        tmdb_api_key=encrypt_secret("from-settings"),
    )
    keys = integrations.resolve_integrations(row)  # type: ignore[arg-type]
    assert keys.tmdb_api_key == "from-settings" and keys.sources["tmdb_api_key"] == "database"
    assert keys.omdb_api_key == "omdb-env" and keys.sources["omdb_api_key"] == "environment"
    assert keys.tvdb_api_key is None and "tvdb_api_key" not in keys.sources
