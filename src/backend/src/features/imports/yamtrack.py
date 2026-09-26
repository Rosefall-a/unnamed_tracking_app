"""Parser for YamTrack's native CSV export format.

YamTrack exports one row for a movie/show plus optional season and episode
rows.  This parser intentionally accepts both the compact export columns and
newer exports with additional metadata columns.  Unsupported media types are
reported to the caller instead of aborting the whole import.
"""

from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from src.features.imports.lists import ImportedTitle


class YamtrackImportError(ValueError):
    pass


MAX_BYTES = 30 * 1024 * 1024
_SUPPORTED_TYPES = {"movie", "tv"}
_ANIME_TYPES = {"anime"}
_STATUS_MAP = {
    "completed": "WATCHED",
    "complete": "WATCHED",
    "watched": "WATCHED",
    "in progress": "IN_PROGRESS",
    "in_progress": "IN_PROGRESS",
    "watching": "IN_PROGRESS",
    "paused": "IN_PROGRESS",
    "planning": "WATCHLIST",
    "planned": "WATCHLIST",
    "watchlist": "WATCHLIST",
    "backlog": "BACKLOG",
    "dropped": "DROPPED",
    "rewatch": "REWATCH",
    "favorite": "FAVORITE",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int(value: str) -> int | None:
    try:
        return int(float(value)) if value else None
    except (TypeError, ValueError):
        return None


def _decimal(value: str) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _day(value: str) -> date | None:
    value = _text(value)
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _status(value: str) -> str:
    normalized = _text(value).lower().replace("-", " ")
    return _STATUS_MAP.get(normalized, "WATCHLIST")


def _rows(raw: bytes) -> list[dict[str, str]]:
    if len(raw) > MAX_BYTES:
        raise YamtrackImportError("The YamTrack CSV is too large (30 MB maximum).")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise YamtrackImportError("The YamTrack export must be a UTF-8 CSV file.") from exc
    reader = csv.DictReader(io.StringIO(text))
    fields = {f.strip() for f in (reader.fieldnames or []) if f}
    required = {"media_id", "source", "media_type"}
    if not required.issubset(fields):
        raise YamtrackImportError(
            "This does not look like a YamTrack export. Expected media_id, source and media_type columns."
        )
    return [{(k or "").strip(): _text(v) for k, v in row.items()} for row in reader]


@dataclass
class YamtrackEntry:
    """One importable movie or TV title plus its episode progress."""

    item: ImportedTitle
    media_id: str
    source: str
    episodes_by_season: dict[int, set[int]] = field(default_factory=lambda: defaultdict(set))
    season_completed: set[int] = field(default_factory=set)

    @property
    def episodes_watched(self) -> int:
        return sum(len(values) for values in self.episodes_by_season.values())


def parse_yamtrack(raw: bytes) -> tuple[list[YamtrackEntry], int]:
    """Parse a YamTrack export.

    The title row is authoritative for status/score/dates/notes. Episode rows
    are folded into progress so a TV migration does not lose watched episodes.
    Seasons and unsupported media types are not emitted as standalone titles.
    """
    rows = _rows(raw)
    entries: dict[tuple[str, str, str], YamtrackEntry] = {}
    skipped = 0

    for row in rows:
        media_type = _text(row.get("media_type")).lower()
        source = _text(row.get("source"))
        media_id = _text(row.get("media_id"))
        if not media_id:
            skipped += 1
            continue

        # Episode/season rows are progress information for the parent TV title.
        if media_type in {"season", "episode"}:
            if source == "" or media_id == "":
                skipped += 1
                continue
            key = (media_id, source, "tv")
            entry = entries.get(key)
            if entry is None:
                # A valid TV row may appear later in the file; create a
                # placeholder so progress is retained either way.
                entry = YamtrackEntry(
                    ImportedTitle("tv", _text(row.get("series_name")) or "", None, "WATCHLIST"),
                    media_id,
                    source,
                )
                entries[key] = entry
            season = _int(row.get("season_number", ""))
            episode = _int(row.get("episode_number", ""))
            if media_type == "episode" and season is not None and episode is not None:
                if _status(row.get("status", "")) == "WATCHED" or _text(row.get("end_date")):
                    entry.episodes_by_season[season].add(episode)
            elif media_type == "season" and season is not None and _status(row.get("status", "")) == "WATCHED":
                entry.season_completed.add(season)
            continue

        if media_type in _ANIME_TYPES:
            # Anime support is deliberately left to the existing MAL/AniList
            # importers because YamTrack anime IDs can come from several
            # providers and are not interchangeable with the app's IDs.
            skipped += 1
            continue
        if media_type not in _SUPPORTED_TYPES:
            skipped += 1
            continue

        title = _text(row.get("title"))
        if not title:
            skipped += 1
            continue
        key = (media_id, source, media_type)
        status = _status(row.get("status", ""))
        progress = _int(row.get("progress", "")) or 0
        entry = entries.get(key)
        if entry is None:
            entry = YamtrackEntry(
                ImportedTitle(
                    kind=media_type,
                    title=title,
                    year=None,
                    status=status,
                    rating=_decimal(row.get("score", "")),
                    watched_on=_day(row.get("end_date", "")),
                ),
                media_id,
                source,
            )
            entries[key] = entry
        else:
            # Prefer the actual title row over a placeholder created by an
            # episode/season row earlier in the file.
            entry.item.title = title
            entry.item.status = status
            entry.item.rating = _decimal(row.get("score", ""))
            entry.item.watched_on = _day(row.get("end_date", ""))

        if media_type == "movie" and progress > 0 and status == "WATCHLIST":
            entry.item.status = "WATCHED"

    # A completed season row can tell us the show was watched even if an export
    # has no episode rows. Do not invent an episode count; metadata refresh can
    # supply the season lengths later.
    result: list[YamtrackEntry] = []
    for entry in entries.values():
        if not entry.item.title:
            skipped += 1
            continue
        if entry.season_completed and entry.item.status == "WATCHLIST":
            entry.item.status = "WATCHED"
        result.append(entry)
    if not result:
        raise YamtrackImportError("No supported movies or TV shows were found in this YamTrack export.")
    return result, skipped
