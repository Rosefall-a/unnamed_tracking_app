"""A readable copy of a game's details in its folder, so the library still makes
sense on disk without the app. The database stays the real copy: nothing reads
this file back, and failing to write it never fails what asked for it."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any

from src.database.models.game import Game
from src.helpers.save_game_asset import DATA_ROOT, create_game_folder

logger = logging.getLogger(__name__)

INFO_FILENAME = "game.json"
_FIELDS = (
    "title",
    "source",
    "external_id",
    "status",
    "favorite",
    "description",
    "developer",
    "publisher",
    "series",
    "release_date",
    "age_rating",
    "platform",
    "tags",
    "features",
    "collections",
    "time_to_beat_hours",
    "time_to_beat_extras_hours",
    "time_to_beat_completionist_hours",
    "time_to_beat_all_hours",
    "playtime_seconds",
    "rating_overall",
    "rating_story",
    "rating_gameplay",
    "rating_soundtrack",
    "completion_date",
    "notes",
)


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def has_info_file(game: Game) -> bool:
    folder = DATA_ROOT / str(game.user_id) / "games" / (game.folder_location or "")
    return bool(game.folder_location) and (folder / INFO_FILENAME).is_file()


def write_game_info(game: Game) -> bool:
    if not game.folder_location:
        return False
    data = {field: _plain(getattr(game, field)) for field in _FIELDS}
    data["saved_at"] = int(time.time())
    try:
        folder = create_game_folder(game.user_id, game.folder_location)
        temporary = folder / f".{INFO_FILENAME}.tmp"
        temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        # a crash part way through leaves the old file, never half of a new one
        os.replace(temporary, folder / INFO_FILENAME)
    except OSError:
        logger.warning("Could not write the info file of game %s", game.id, exc_info=True)
        return False
    return True
