"""Shared game-route ownership, paths, validation, and metadata-history helpers."""

import re
import time
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID

from fastapi import (
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.titles import derive_sort_title as _derive_sort_title
from src.database.models.game import Game
from src.database.models.game_field_change import GameFieldChange
from src.database.models.game_note_detail import GameNoteDetail
from src.database.models.user_scan_settings import UserScanSettings
from src.features import game_notes

__all__ = ["_derive_sort_title"]

_DATA_ROOT = Path("/data/users")


_NOTE_NAME_PATTERN = re.compile(r"^[^\x00-\x1f\x7f/\\]+$")


ALLOWED_ASSET_KINDS = {"key_art", "banner", "logo", "icon"}


# History fields deliberately mirror the public game metadata contract.
# pylint: disable=duplicate-code
FIELD_CHANGE_TRACKED_FIELDS = {
    "developer",
    "publisher",
    "series",
    "tags",
    "features",
    "description",
    "age_rating",
    "release_date",
    "time_to_beat_hours",
    # what the history timeline shows as "changed status" and "changed price"
    "status",
    "purchase_price",
    "purchase_price_currency_code",
    "purchase_date",
}
# pylint: enable=duplicate-code


_NON_NULLABLE_UPDATE_FIELDS = frozenset(
    {
        "title",
        "sort_title",
        "created_at",
        "folder_location",
        "status",
        "favorite",
        "profiles_enabled",
        "osrs_stats_enabled",
        "playtime_seconds",
        "tags",
        "features",
        "collections",
    }
)


def _scan_settings_to_preferences(scan_settings: UserScanSettings) -> dict:
    return {
        "provider_order": scan_settings.provider_order,
        "image_provider_order": scan_settings.image_provider_order,
        "save_developer": scan_settings.save_developer,
        "save_publisher": scan_settings.save_publisher,
        "save_series": scan_settings.save_series,
        "save_tags": scan_settings.save_tags,
        "save_features": scan_settings.save_features,
        "save_description": scan_settings.save_description,
        "save_age_rating": scan_settings.save_age_rating,
        "save_release_date": scan_settings.save_release_date,
        "save_time_to_beat": scan_settings.save_time_to_beat,
        "save_key_art": scan_settings.save_key_art,
        "save_banner": scan_settings.save_banner,
        "save_logo": scan_settings.save_logo,
        "save_icon": scan_settings.save_icon,
    }


def _field_change_value_to_text(value: object, field: str = "") -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, Decimal | float):
        # 59.9 and Decimal("59.90") are the same price, not a change
        return f"{Decimal(str(value)).normalize():f}"
    if isinstance(value, int) and not isinstance(value, bool) and field.endswith("_date"):
        return datetime.fromtimestamp(value, UTC).strftime("%Y-%m-%d")
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else None
    return str(value)


def _record_field_changes(game: Game, updates: dict, db: AsyncSession) -> None:
    now = int(time.time())
    for field in FIELD_CHANGE_TRACKED_FIELDS & updates.keys():
        old_text = _field_change_value_to_text(getattr(game, field), field)
        new_text = _field_change_value_to_text(updates[field], field)
        if old_text == new_text:
            continue
        db.add(
            GameFieldChange(
                game_id=game.id,
                field_name=field,
                old_value=old_text,
                new_value=new_text,
                changed_at=now,
            )
        )


def _drop_nulls_for_required_fields(updates: dict) -> dict:
    cleaned = {
        field: value
        for field, value in updates.items()
        if value is not None or field not in _NON_NULLABLE_UPDATE_FIELDS
    }
    # a cleared sorting name is still a request: re-derive it from the title
    if "sort_title" in updates and updates["sort_title"] is None:
        cleaned["sort_title"] = ""
    return cleaned


def _duplicate_folder_error(folder_name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": "duplicate_folder_location",
            "field": "folder_location",
            "value": folder_name,
            "message": f"A game with folder_location '{folder_name}' already exists.",
        },
    )


async def _ensure_folder_location_available(
    folder_name: str,
    user_id: UUID,
    db: AsyncSession,
    exclude_game_id: UUID | None = None,
) -> None:
    stmt = select(Game.id).where(
        Game.user_id == user_id,
        Game.folder_location == folder_name,
        Game.deleted_at.is_(None),
    )
    if exclude_game_id is not None:
        stmt = stmt.where(Game.id != exclude_game_id)

    existing = await db.scalar(stmt)
    if existing is not None:
        raise _duplicate_folder_error(folder_name)


# Keep the established workflow and public parameters together.
# pylint: disable=too-many-boolean-expressions
def _normalize_note_name(note_name: str) -> str:
    normalized = note_name.strip()
    if normalized.lower().endswith(".md"):
        normalized = normalized[:-3]

    if (
        not normalized
        or normalized in {".", ".."}
        or normalized.startswith(".")
        or normalized.endswith(".")
        or normalized.endswith(" ")
        or ":" in normalized
        or not _NOTE_NAME_PATTERN.fullmatch(normalized)
        or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])", normalized)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_note_name",
                "message": (
                    "Note title must be a normal file name: spaces and common punctuation are allowed, "
                    "but path separators, control characters, absolute paths, drive-style names, "
                    "and path-like titles are not allowed."
                ),
            },
        )
    return normalized


# pylint: enable=too-many-boolean-expressions


def _game_note_path(game: Game, note_name: str) -> Path:
    if not game.folder_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game folder_location is missing.",
        )

    note_file_name = f"{_normalize_note_name(note_name)}.md"
    note_dir = _DATA_ROOT / str(game.user_id) / "games" / game.folder_location / "notes"
    note_dir.mkdir(parents=True, exist_ok=True)
    return note_dir / note_file_name


async def _get_game_or_404(
    game_id: UUID, db: AsyncSession, user_id: UUID, include_deleted: bool = False
) -> Game:
    stmt = select(Game).where(Game.id == game_id, Game.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(Game.deleted_at.is_(None))
    game = await db.scalar(stmt)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )
    return game


def _note_summary(path: Path, row: GameNoteDetail | None = None) -> dict:
    """What a note card shows: its name, when it was created and last edited,
    how long it is, checklist progress, the start of it, and its pin, tags and
    achievement. Text comes from the file; the rest from its details row."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    stat = path.stat()
    done, total = game_notes.task_counts(text)
    return {
        "name": path.stem,
        "created_at": row.created_at if row else int(stat.st_mtime),
        "updated_at": int(stat.st_mtime),
        "size": stat.st_size,
        "words": len(text.split()),
        "preview": text[:600],
        "tasks_done": done,
        "tasks_total": total,
        "pinned": row.pinned if row else False,
        "tags": row.tags if row else [],
        "linked_achievement_id": str(row.linked_achievement_id)
        if row and row.linked_achievement_id
        else None,
    }
