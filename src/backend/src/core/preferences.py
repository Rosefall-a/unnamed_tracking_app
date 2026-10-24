"""Server-side per-user preferences: defaults live here, the database row
(UserPreferences.data) only stores what the user changed. Adding an
option is a one-line change to DEFAULTS, not a migration."""

import json
import re
import time
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.page_settings import DEFAULT_PAGE_SETTINGS, validate_page_settings
from src.database.models.user_preferences import UserPreferences

DEFAULTS: dict[str, Any] = {
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
    # a film, OVA or special listed for something you finished
    "notify_extras_announced": False,
    "notify_movie_released": True,
    "notify_statuses": ["watching", "plan", "hold"],
    "notify_media_types": ["anime", "tv", "movie"],
    "notification_retention_days": 30,
    # days a deleted movie, show or anime stays in the trash before it is deleted for good (0 = never)
    "media_trash_retention_days": 0,
    "library_default_layout": "list",
    "title_language": "english",
    "lists_default_sort": "custom",
    "stats_include_plan": True,
    "anilist_import_enabled": False,
    "anilist_import_username": "",
    "anilist_import_interval_minutes": 24 * 60,
    "anilist_import_update_existing": False,
    "anilist_import_last_run_at": None,
    # genres from the tags Steam players vote on (Souls-like, Open World ...)
    # instead of only Steam's broad official genres
    "steam_user_tags": True,
    # also add the Steam wishlist, as Wishlist games, when importing from Steam
    "steam_import_wishlist": False,
    # what every game page shows (tabs, buttons); a game can override it
    "game_page": DEFAULT_PAGE_SETTINGS,
    # the Home page: pages of widgets placed on a grid. None until the user
    # customises it, so the app's default layout can improve without a migration.
    "home_layout": None,
    # colours the user has changed from the app's own (accent, text and so on), by name
    "theme_colors": {},
    # games the sync grouped by franchise or by where they came from: shown on
    # their own tab of Collections, mixed in with the user's own, or not at all
    "collections_auto": "tab",
}

_CHOICES: dict[str, tuple[Any, ...]] = {
    "calendar_default_view": ("month", "week", "agenda"),
    "calendar_week_start": (0, 1),
    "notification_retention_days": (0, 7, 14, 30, 90),
    "media_trash_retention_days": (0, 7, 14, 30, 90),
    "library_default_layout": ("list", "shelf", "board"),
    "lists_default_sort": ("custom", "name", "count", "recent"),
    "title_language": ("english", "romaji", "native"),
    "collections_auto": ("tab", "mixed", "hidden"),
}

_SET_CHOICES: dict[str, tuple[str, ...]] = {
    "notify_statuses": ("watching", "plan", "hold"),
    "calendar_airing_statuses": ("watching", "plan", "hold"),
    "notify_media_types": ("anime", "tv", "movie"),
}


_HOME_MAX_PAGES = 8
_HOME_MAX_WIDGETS = 60
_HOME_MAX_BYTES = 64 * 1024


def _home_int(value: Any, name: str, low: int, high: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise ValueError(f"home_layout {name} must be a whole number from {low} to {high}")
    return value


def _home_text(value: Any, name: str, longest: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > longest:
        raise ValueError(f"home_layout {name} must be text of 1 to {longest} characters")
    return value


def validate_home_layout(value: Any) -> Any:
    """The shape of the Home layout, not what the widgets mean: the app decides
    which widget types exist, so a widget it no longer knows is kept and shown
    as a placeholder instead of being rejected here."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("home_layout must be an object or null")
    pages = value.get("pages")
    if not isinstance(pages, list) or not 1 <= len(pages) <= _HOME_MAX_PAGES:
        raise ValueError(f"home_layout needs 1 to {_HOME_MAX_PAGES} pages")
    clean_pages = []
    seen_pages: set[str] = set()
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("each home_layout page must be an object")
        page_id = _home_text(page.get("id"), "page id", 40)
        if page_id in seen_pages:
            raise ValueError("home_layout page ids must be unique")
        seen_pages.add(page_id)
        options = page.get("options", {})
        widgets = page.get("widgets")
        if not isinstance(options, dict) or not isinstance(widgets, list):
            raise ValueError("home_layout pages need options and widgets")
        if len(widgets) > _HOME_MAX_WIDGETS:
            raise ValueError(f"a Home page holds at most {_HOME_MAX_WIDGETS} widgets")
        clean_widgets = []
        seen_widgets: set[str] = set()
        for widget in widgets:
            if not isinstance(widget, dict):
                raise ValueError("each widget must be an object")
            widget_id = _home_text(widget.get("id"), "widget id", 60)
            if widget_id in seen_widgets:
                raise ValueError("home_layout widget ids must be unique")
            seen_widgets.add(widget_id)
            settings = widget.get("settings", {})
            if not isinstance(settings, dict):
                raise ValueError("widget settings must be an object")
            variant = widget.get("variant")
            if variant is not None:
                variant = _home_text(variant, "variant", 40)
            clean_widgets.append(
                {
                    "id": widget_id,
                    "type": _home_text(widget.get("type"), "type", 60),
                    "x": _home_int(widget.get("x"), "x", 0, 11),
                    "y": _home_int(widget.get("y"), "y", 0, 400),
                    "w": _home_int(widget.get("w"), "w", 1, 12),
                    "h": _home_int(widget.get("h"), "h", 1, 40),
                    "settings": settings,
                    "variant": variant,
                }
            )
        clean_pages.append(
            {
                "id": page_id,
                "name": _home_text(page.get("name"), "page name", 40),
                "options": options,
                "widgets": clean_widgets,
            }
        )
    clean = {"version": _home_int(value.get("version", 1), "version", 1, 1000), "pages": clean_pages}
    if len(json.dumps(clean)) > _HOME_MAX_BYTES:
        raise ValueError("home_layout is too large")
    return clean


_THEME_COLOR_KEYS = ("accent", "text", "dim", "heading", "background", "panels")
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def validate_theme_colors(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("theme_colors must be an object")
    clean: dict[str, str] = {}
    for key, color in value.items():
        if key not in _THEME_COLOR_KEYS:
            raise ValueError(f"theme_colors has no colour called {key!r}")
        if not isinstance(color, str) or not _HEX_COLOR.match(color):
            raise ValueError(f"theme_colors {key} must be a colour like #d68a34")
        clean[key] = color.lower()
    return clean


def validate_preference(key: str, value: Any) -> Any:
    if key not in DEFAULTS:
        raise ValueError(f"Unknown preference {key!r}")
    default = DEFAULTS[key]
    if key == "game_page":
        return validate_page_settings(value, partial=False)
    if key == "home_layout":
        return validate_home_layout(value)
    if key == "theme_colors":
        return validate_theme_colors(value)
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


# Earlier Home layouts, newest first, so a bad edit or a deleted page can be
# undone. Kept beside the preferences but never sent with them (it can be large)
# and never written by the app directly: saving a new layout files the old one.
HOME_HISTORY_KEY = "home_layout_history"
_HOME_HISTORY_MAX = 15
# typing in a note saves the layout every moment; those settings-only saves keep
# at most one earlier version per this many seconds
_HOME_HISTORY_SETTINGS_GAP = 10 * 60


def _layout_shape(layout: Any) -> Any:
    """The layout without what widgets hold (a note's text): pages, and where
    each widget is and what it is."""
    return [
        (
            page["id"],
            page["name"],
            json.dumps(page["options"], sort_keys=True),
            [(w["id"], w["type"], w["x"], w["y"], w["w"], w["h"], w["variant"]) for w in page["widgets"]],
        )
        for page in layout["pages"]
    ]


def _file_previous_home_layout(data: dict[str, Any], new: Any, now: int) -> None:
    previous = data.get("home_layout")
    if previous is None or previous == new:
        return
    history = list(data.get(HOME_HISTORY_KEY) or [])
    settings_only = new is not None and _layout_shape(previous) == _layout_shape(new)
    if settings_only and history and now - history[0]["replaced_at"] < _HOME_HISTORY_SETTINGS_GAP:
        return
    history.insert(0, {"replaced_at": now, "layout": previous})
    data[HOME_HISTORY_KEY] = history[:_HOME_HISTORY_MAX]


def _public(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if k != HOME_HISTORY_KEY}


async def load_preferences(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
    row = await db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))
    return {**DEFAULTS, **_public(row.data if row else {})}


async def load_home_layout_history(db: AsyncSession, user_id: UUID) -> list[dict[str, Any]]:
    row = await db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))
    return list((row.data if row else {}).get(HOME_HISTORY_KEY) or [])


async def save_preferences(
    db: AsyncSession, user_id: UUID, changes: dict[str, Any]
) -> dict[str, Any]:
    clean = {k: validate_preference(k, v) for k, v in changes.items()}
    row = await db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))
    if row is None:
        row = UserPreferences(user_id=user_id, data={})
        db.add(row)
    data = dict(row.data)
    if "home_layout" in clean:
        _file_previous_home_layout(data, clean["home_layout"], int(time.time()))
    row.data = {**data, **clean}
    await db.commit()
    return {**DEFAULTS, **_public(row.data)}
