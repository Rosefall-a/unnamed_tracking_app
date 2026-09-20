"""Pytest setup shared by backend tests."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config


def pytest_configure() -> None:
    """Prepare the CI database when a test database URL is configured."""
    if not os.environ.get("DATABASE_URL"):
        return

    backend_root = Path(__file__).resolve().parents[1]
    data_dir = Path(os.environ.get("APP_DATA_DIR", backend_root / ".test-data"))
    data_dir.mkdir(parents=True, exist_ok=True)

    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option(
        "script_location",
        str(backend_root / "src" / "database" / "migrations"),
    )
    config.set_main_option("prepend_sys_path", str(backend_root))
    command.upgrade(config, "head")
