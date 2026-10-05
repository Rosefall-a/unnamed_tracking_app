"""Server-side per-user preferences: defaults live here, the database row
(UserPreferences.data) only stores what the user changed. Adding an
option is a one-line change to DEFAULTS, not a migration."""

import math
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.user_preferences import UserPreferences
from src.helpers.shortcut_keys import validate_shortcut_overrides

DEFAULTS: dict[str, Any] = {
    "ui_theme": "system",
    "ui_theme_package": "server",
    "ui_palette": "orange",
    "ui_custom_palette": {},
    "ui_density": "comfortable",
    "ui_style": "archive-pocket",
    "ui_reduce_motion": False,
    "ui_high_contrast": False,
    "ui_welcome_completed": False,
    "keyboard_shortcuts_enabled": True,
    "keyboard_shortcut_overrides": {},
    "home_widgets": [],
    "home_widget_config": {},
    "calendar_game_releases": True,
    "calendar_game_history": True,
    "calendar_default_view": "month",
    "calendar_week_start": 0,
    "calendar_hide_games": False,
    "calendar_show_estimated": True,
    "calendar_airing_statuses": ["watching", "plan", "hold"],
    "notify_episode_aired": True,
    "notify_season_started": True,
    "notify_sequel_announced": True,
    "notify_movie_released": True,
    "notify_session_anomaly": True,
    "notify_statuses": ["watching", "plan", "hold"],
    "notify_media_types": ["anime", "tv", "movie"],
    "notification_retention_days": 30,
    "library_default_layout": "list",
    "title_language": "english",
    "lists_default_sort": "custom",
    "stats_include_plan": True,
    "anilist_import_enabled": False,
    "anilist_import_username": "",
    "anilist_import_interval_minutes": 24 * 60,
    "anilist_import_update_existing": False,
    "anilist_import_last_run_at": None,
}

_CHOICES: dict[str, tuple[Any, ...]] = {
    "ui_theme": ("system", "light", "dark"),
    "ui_palette": ("orange", "green", "custom"),
    "ui_density": ("comfortable", "compact"),
    "ui_style": ("archive-pocket",),
    "calendar_default_view": ("month", "week", "agenda"),
    "calendar_week_start": (0, 1),
    "notification_retention_days": (0, 7, 14, 30, 90),
    "library_default_layout": ("list", "shelf", "board"),
    "lists_default_sort": ("custom", "name", "count", "recent"),
    "title_language": ("english", "romaji", "native"),
}

_SET_CHOICES: dict[str, tuple[str, ...]] = {
    "notify_statuses": ("watching", "plan", "hold"),
    "calendar_airing_statuses": ("watching", "plan", "hold"),
    "notify_media_types": ("anime", "tv", "movie"),
}

_HOME_CORE_WIDGETS = {
    "library-summary",
    "continue-playing",
    "recently-added",
    "goals",
    "random-picker",
    "backlog",
    "on-this-day",
    "weekly-digest",
    "getting-started",
}


def _validate_home_widgets(value: Any) -> list[str]:
    """Preserve order and unavailable plugin selections, bounded as plain identifiers."""
    if not isinstance(value, list) or len(value) > 32:
        raise ValueError("home_widgets must be a list of at most 32 widget identifiers")
    seen: set[str] = set()
    for identifier in value:
        if not isinstance(identifier, str) or len(identifier) > 512 or identifier in seen:
            raise ValueError("home_widgets must contain unique, bounded string identifiers")
        seen.add(identifier)
        if identifier in _HOME_CORE_WIDGETS:
            continue
        if identifier.startswith("collection:") and identifier[11:].strip():
            continue
        if re.fullmatch(r"plugin:[a-zA-Z0-9._-]{1,128}:[a-zA-Z0-9._-]{1,128}", identifier):
            continue
        raise ValueError(f"Unsupported Home widget identifier {identifier!r}")
    return list(value)


def validate_preference(key: str, value: Any) -> Any:
    if key not in DEFAULTS:
        raise ValueError(f"Unknown preference {key!r}")
    default = DEFAULTS[key]
    if key == "ui_theme_package":
        if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", value):
            raise ValueError("ui_theme_package must be a bounded theme identifier")
        return value
    if key == "home_widgets":
        return _validate_home_widgets(value)
    if key == "home_widget_config":
        return _validate_widget_config(value)
    if key == "ui_custom_palette":
        return _validate_custom_palette(value)
    if key == "keyboard_shortcut_overrides":
        return validate_shortcut_overrides(value)
    if key in _SET_CHOICES:
        allowed = _SET_CHOICES[key]
        if not isinstance(value, list) or any(v not in allowed for v in value):
            raise ValueError(f"{key} must be a list drawn from {list(allowed)}")
        return [v for v in allowed if v in value]
    if key in _CHOICES:
        if value not in _CHOICES[key]:
            raise ValueError(f"{key} must be one of {list(_CHOICES[key])}")
        return value
    if key == "anilist_import_username":
        if not isinstance(value, str) or len(value.strip()) > 100:
            raise ValueError("anilist_import_username must be a string of at most 100 characters")
        return value.strip()
    if key == "anilist_import_interval_minutes":
        if not isinstance(value, int) or isinstance(value, bool) or not 60 <= value <= 30 * 24 * 60:
            raise ValueError("anilist_import_interval_minutes must be between 60 and 43200")
        return value
    if key == "anilist_import_last_run_at":
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value < 0
        ):
            raise ValueError("anilist_import_last_run_at must be a Unix timestamp or null")
        return value
    if isinstance(default, bool):
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be true or false")
        return value
    return value


def _validate_custom_palette(value: Any) -> dict[str, dict[str, str]]:
    """Allow bounded plain colors for personal palettes, never arbitrary CSS."""
    roles = {
        "background",
        "surface",
        "surface_alt",
        "text",
        "muted",
        "accent",
        "success",
        "warning",
        "error",
        "info",
        "purple",
    }
    if value == {}:
        return {}
    if not isinstance(value, dict) or set(value) != {"light", "dark"}:
        raise ValueError("custom palettes require light and dark color sets")
    for colors in value.values():
        if (
            not isinstance(colors, dict)
            or set(colors) != roles
            or any(
                not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color)
                for color in colors.values()
            )
        ):
            raise ValueError("custom palettes require all eleven roles as six-digit hex colors")
    return {
        mode: {role: color.lower() for role, color in colors.items()}
        for mode, colors in value.items()
    }


def _validate_widget_config(value: Any) -> dict[str, dict[str, Any]]:
    """Bound non-secret personal options without requiring an installed plugin."""
    if not isinstance(value, dict) or len(value) > 32:
        raise ValueError("home_widget_config must contain at most 32 widget configurations")
    for identifier, options in value.items():
        if not isinstance(identifier, str) or not re.fullmatch(
            r"plugin:[a-zA-Z0-9._-]{1,128}:[a-zA-Z0-9._-]{1,128}", identifier
        ):
            raise ValueError("widget configuration requires a valid plugin widget identifier")
        if not isinstance(options, dict) or len(options) > 16:
            raise ValueError("each widget configuration must contain at most 16 fields")
        for field, option in options.items():
            if not isinstance(field, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", field):
                raise ValueError("widget configuration contains an invalid field identifier")
            if isinstance(option, str) and len(option) <= 2048:
                continue
            if isinstance(option, int) and abs(option) <= 9_007_199_254_740_991:
                continue
            if isinstance(option, float) and math.isfinite(option):
                continue
            if (
                isinstance(option, list)
                and len(option) <= 32
                and all(isinstance(item, str) and len(item) <= 256 for item in option)
            ):
                continue
            raise ValueError(
                "widget options must be bounded strings, finite numbers or string lists"
            )
    return {identifier: dict(options) for identifier, options in value.items()}


async def load_preferences(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
    row = await db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))
    return {**DEFAULTS, **(row.data if row else {})}


async def save_preferences(
    db: AsyncSession, user_id: UUID, changes: dict[str, Any]
) -> dict[str, Any]:
    clean = {k: validate_preference(k, v) for k, v in changes.items()}
    row = await db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))
    if row is None:
        row = UserPreferences(user_id=user_id, data={})
        db.add(row)
    row.data = {**row.data, **clean}
    await db.commit()
    return {**DEFAULTS, **row.data}
