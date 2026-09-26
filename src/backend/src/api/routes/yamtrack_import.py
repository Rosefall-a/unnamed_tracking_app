"""Import YamTrack's native CSV export into the media library."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database.models.tv_show import TVSeason, TVShow, TVShowStatus
from src.database.models.user import User
from src.database.session import get_db
from src.features.imports.list_apply import (
    apply_tracking,
    differences,
    fill_details,
    match_titles,
    new_title,
)
from src.features.imports.yamtrack import (
    MAX_BYTES,
    YamtrackEntry,
    YamtrackImportError,
    parse_yamtrack,
)

router = APIRouter(prefix="/api", tags=["import"], dependencies=[Depends(get_current_user)])


class YamtrackPreview(BaseModel):
    total: int
    new_count: int
    new_titles: list[str]
    existing: list[dict[str, Any]]
    identical: int
    skipped_other: int


class YamtrackImportResult(BaseModel):
    created: int
    updated: int
    kept: int
    total_in_file: int
    skipped_other: int
    details_filled: int
    details_not_found: int
    details_unavailable: bool
    details_source: str | None = None
    episodes_imported: int


async def _read(file: UploadFile) -> tuple[list[YamtrackEntry], int]:
    raw = await file.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The YamTrack CSV is too large (30 MB maximum).",
        )
    try:
        return parse_yamtrack(raw)
    except YamtrackImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _match_items(entries: list[YamtrackEntry]):
    return [entry.item for entry in entries]


def _apply_progress(row: TVShow, entry: YamtrackEntry) -> int:
    """Apply watched episode numbers without inventing episode counts."""
    imported = 0
    seasons = {s.season_number: s for s in row.seasons}
    for season_number, episodes in entry.episodes_by_season.items():
        season = seasons.get(season_number)
        if season is None:
            season = TVSeason(
                season_number=season_number,
                episode_count=None,
                episodes_watched=len(episodes),
                status=TVShowStatus.IN_PROGRESS,
            )
            row.seasons.append(season)
        else:
            season.episodes_watched = len(episodes)
            if season.episode_count and len(episodes) >= season.episode_count:
                season.status = TVShowStatus.WATCHED
        imported += len(episodes)
    for season_number in entry.season_completed:
        season = seasons.get(season_number)
        if season is not None and season.episode_count:
            season.episodes_watched = season.episode_count
            season.status = TVShowStatus.WATCHED
    return imported


def _apply_notes(row: Any, entry: YamtrackEntry) -> None:
    if entry.notes and hasattr(row, "note"):
        row.note = entry.notes


@router.post("/import/yamtrack/preview", response_model=YamtrackPreview)
async def preview_yamtrack(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> YamtrackPreview:
    entries, skipped = await _read(file)
    matches = await match_titles(db, current_user.id, _match_items(entries))
    new = [m.imported for m in matches if m.existing is None]
    existing = [
        {
            "yamtrack_id": entries[i].media_id,
            "title": m.imported.title,
            "site_title": m.existing.title,
            "differences": differences(m.existing, m.imported),
        }
        for i, m in enumerate(matches)
        if m.existing is not None
    ]
    return YamtrackPreview(
        total=len(entries),
        new_count=len(new),
        new_titles=[i.title for i in new[:20]],
        existing=[e for e in existing if e["differences"]],
        identical=sum(1 for e in existing if not e["differences"]),
        skipped_other=skipped,
    )


@router.post("/import/yamtrack", response_model=YamtrackImportResult)
async def import_yamtrack(
    file: UploadFile,
    overwrite: str = Form("[]"),
    fetch_details: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> YamtrackImportResult:
    try:
        chosen = {str(x) for x in json.loads(overwrite)}
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="overwrite must be a JSON list."
        ) from exc

    entries, skipped = await _read(file)
    matches = await match_titles(db, current_user.id, _match_items(entries))
    created = updated = kept = 0
    touched: list[tuple[Any, Any, bool]] = []

    for entry, match in zip(entries, matches):
        item = entry.item
        if match.existing is not None:
            picked = entry.media_id in chosen or item.key in chosen
            if picked:
                apply_tracking(match.existing, item)
                _apply_notes(match.existing, entry)
                updated += 1
            else:
                kept += 1
            touched.append((item, match.existing, picked))
            continue

        row = new_title(current_user.id, item)
        db.add(row)
        _apply_notes(row, entry)
        created += 1
        touched.append((item, row, True))

    details = {"filled": 0, "not_found": 0, "seasons_assumed_watched": 0}
    unavailable = False
    details_source: str | None = None
    if fetch_details and touched:
        from src.core.app_integrations import get_or_create_app_integration_settings
        from src.core.integrations import resolve_integrations
        from src.features.imports.list_apply import OmdbLookup
        from src.features.metadata.movies.omdb import OMDBClient
        from src.features.metadata.movies.tmdb import TMDBClient

        keys = resolve_integrations(await get_or_create_app_integration_settings(db))
        if keys.tmdb_api_key:
            details_source = "TMDB"
            details = await fill_details(TMDBClient(keys.tmdb_api_key), touched)
        elif keys.omdb_api_key:
            details_source = "OMDb"
            details = await fill_details(OmdbLookup(OMDBClient(keys.omdb_api_key)), touched)
        else:
            unavailable = True

    # Apply episode progress after metadata lookup so known season rows are
    # reused when possible. This is deliberately done once to keep the result
    # count accurate and make repeated imports idempotent.
    episodes_imported = 0
    for entry, (_, row, picked) in zip(entries, touched):
        if picked and isinstance(row, TVShow):
            episodes_imported += _apply_progress(row, entry)

    await db.commit()
    return YamtrackImportResult(
        created=created,
        updated=updated,
        kept=kept,
        total_in_file=len(entries),
        skipped_other=skipped,
        details_filled=details["filled"],
        details_not_found=details["not_found"],
        details_unavailable=unavailable,
        details_source=details_source,
        episodes_imported=episodes_imported,
    )
