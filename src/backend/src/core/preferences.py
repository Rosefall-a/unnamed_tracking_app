"""Server-side per-user preferences: defaults live here, the database row
(UserPreferences.data) only stores what the user changed. Adding an
option is a one-line change to DEFAULTS, not a migration."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.user_preferences import UserPreferences

DEFAULTS: dict[str, Any] = {
    # calendar
    "calendar_game_releases": False,
    "calendar_game_history": False,
    "calendar_default_view": "month",  # "month" | "agenda"
    "calendar_week_start": 0,  # 0 = Sunday, 1 = Monday
    "calendar_hide_games": False,  # hides every Games layer even if the data exists
    "calendar_show_estimated": True,  # projected later episodes (dashed)
    # notifications
    "notify_episode_aired": True,
    "notify_season_started": True,
    "notify_sequel_announced": True,
    "notify_movie_released": True,
    "notification_retention_days": 30,  # 0 = keep forever
    # library and lists
    "library_default_layout": "list",  # "list" | "shelf" | "board"
    "title_language": "english",  # which spelling of an anime title to show
    "lists_default_sort": "custom",  # "custom" | "name" | "count" | "recent"
    # statistics
    "stats_include_plan": True,  # count Plan to Watch titles in title totals
}

_CHOICES: dict[str, tuple[Any, ...]] = {
    "calendar_default_view": ("month", "agenda"),
    "calendar_week_start": (0, 1),
    "notification_retention_days": (0, 7, 14, 30, 90),
    "library_default_layout": ("list", "shelf", "board"),
    "lists_default_sort": ("custom", "name", "count", "recent"),
    "title_language": ("english", "romaji", "native"),
}


def validate_preference(key: str, value: Any) -> Any:
    """Returns the value if it is a legal setting for `key`, else raises
    ValueError. Unknown keys are rejected so a typo can't silently store
    junk."""
    if key not in DEFAULTS:
        raise ValueError(f"Unknown preference {key!r}")
    default = DEFAULTS[key]
    if key in _CHOICES:
        if value not in _CHOICES[key]:
            raise ValueError(f"{key} must be one of {list(_CHOICES[key])}")
        return value
    if isinstance(default, bool):
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be true or false")
        return value
    return value


async def load_preferences(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
    row = await db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))
    return {**DEFAULTS, **(row.data if row else {})}


async def save_preferences(db: AsyncSession, user_id: UUID, changes: dict[str, Any]) -> dict[str, Any]:
    clean = {k: validate_preference(k, v) for k, v in changes.items()}
    row = await db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))
    if row is None:
        row = UserPreferences(user_id=user_id, data={})
        db.add(row)
    # reassign rather than mutate: SQLAlchemy does not see in-place JSONB edits
    row.data = {**row.data, **clean}
    await db.commit()
    return {**DEFAULTS, **row.data}
