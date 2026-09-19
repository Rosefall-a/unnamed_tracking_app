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
