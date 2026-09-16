from __future__ import annotations

import os
from pathlib import Path

DATA_ROOT = Path(os.getenv("APP_DATA_DIR", "/data"))
USERS_ROOT = DATA_ROOT / "users"
USER_ROOT = DATA_ROOT / "user"
GAMES_ROOT = DATA_ROOT / "games"
BADGES_ROOT = DATA_ROOT / "badges"
BACKUPS_ROOT = DATA_ROOT / "backups"


def ensure_data_directories() -> None:
    """Create the persistent directories used by the application."""
    for path in (USERS_ROOT, USER_ROOT, GAMES_ROOT, BADGES_ROOT, BACKUPS_ROOT):
        path.mkdir(parents=True, exist_ok=True)
