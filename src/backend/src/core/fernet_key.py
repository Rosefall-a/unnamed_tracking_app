"""Persistent installation Fernet key management.

The setup flow may be run without a hand-written SECRET_KEY. A key is generated
once and stored under APP_DATA_DIR/config, then reused for future starts.
"""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import dotenv_values


def _bootstrap_value(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    return str(dotenv_values(".env").get(name) or "").strip()


def _paths() -> tuple[Path, Path, Path]:
    config_dir = Path(_bootstrap_value("APP_DATA_DIR") or "/data") / "config"
    return config_dir / "fernet.key", config_dir / "fernet.key.1", config_dir / "fernet.key.2"


def persistent_fernet_key() -> str:
    """Return the installation key, creating/repairing its persistent copies."""
    paths = _paths()
    env_key = _bootstrap_value("SECRET_KEY")
    valid: list[str] = []
    for path in paths:
        try:
            value = path.read_text(encoding="utf-8").strip()
            Fernet(value.encode())
            valid.append(value)
        except (OSError, ValueError, TypeError):
            pass
    if not valid:
        key = env_key or Fernet.generate_key().decode()
    else:
        counts = Counter(valid)
        key, count = counts.most_common(1)[0]
        if len(valid) >= 2 and count < 2:
            raise RuntimeError(
                "Persistent Fernet key copies disagree. Restore at least two matching "
                f"copies in {paths[0].parent} before starting the application."
            )
    _write_current_key(key, paths)
    return key


def _write_current_key(key: str, paths: tuple[Path, Path, Path]) -> None:
    config_dir = paths[0].parent
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        for path in paths:
            path.write_text(key + "\n", encoding="utf-8")
            path.chmod(0o600)
    except OSError as exc:
        raise RuntimeError(
            f"Could not persist the Fernet key in {config_dir}. "
            "Mount APP_DATA_DIR as a writable persistent volume."
        ) from exc
