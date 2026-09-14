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


def persistent_fernet_key() -> str:
    """Load the installation key from three redundant copies.

    Existing single-key installations are migrated automatically. At startup,
    valid copies are compared and a matching majority is authoritative. A
    single damaged/missing copy is repaired. If two valid copies disagree,
    startup fails closed rather than risking encrypted-secret loss.
    """
    config_dir = Path(_bootstrap_value("APP_DATA_DIR") or "/data") / "config"
    paths = [config_dir / "fernet.key", config_dir / "fernet.key.1", config_dir / "fernet.key.2"]
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
                "The three persistent Fernet key copies do not have a matching "
                "majority. Refusing to start; restore at least two matching "
                f"copies in {config_dir}."
            )

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        for path in paths:
            path.write_text(key + "\n", encoding="utf-8")
            path.chmod(0o600)
    except OSError as exc:
        raise RuntimeError(
            f"Could not persist the Fernet key copies in {config_dir}. "
            "Mount APP_DATA_DIR as a writable persistent volume."
        ) from exc

    return key
