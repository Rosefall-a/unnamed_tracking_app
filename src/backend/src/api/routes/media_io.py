"""Bringing a media list in from elsewhere and getting it out as a table.

- POST /api/import/mal/preview  what a MyAnimeList export would add or change
- POST /api/import/mal      a MyAnimeList export (XML or gzipped XML) -> anime
- POST /api/import/list[/preview]  a Letterboxd or IMDb export -> movies and TV shows
- POST /api/import/media    the app's own JSON export -> movies, TV shows and anime
- GET  /api/export/media.csv  every movie, show and anime as one CSV

The MAL import never changes a title already on the site (same MAL id, or
same title) unless the user picks that title, so importing twice is harmless."""

import csv
import io
import json
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.database.models.anime import Anime
from src.database.models.movies import Movie
from src.database.models.tv_show import TVShow
from src.database.models.user import User
from src.features.imports.yamtrack import build_yamtrack_item, parse_yamtrack

router = APIRouter(prefix="/api/import", tags=["import"])


class YamtrackImportResult(BaseModel):
    created: dict[str, int]
    skipped: dict[str, int]
    total_rows: int
    total_items: int
    seasons_created: int
    episodes_created: int
    errors: list[str]


@router.post("/yamtrack", response_model=YamtrackImportResult)
async def import_yamtrack(file: UploadFile, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> YamtrackImportResult:
    raw = await file.read()
    groups = parse_yamtrack(raw)
    created = {"movies": 0, "tv_shows": 0, "anime": 0}
    skipped = {"movies": 0, "tv_shows": 0, "anime": 0}
    errors: list[str] = []
    seasons_created = episodes_created = 0
    for group in groups:
        key = {"movie": "movies", "tv": "tv_shows", "anime": "anime"}[group.media_type]
        try:
            item = build_yamtrack_item(group); item.user_id = current_user.id
            existing = None
            if group.media_type in {"tv", "anime"}:
                model: Any = TVShow if group.media_type == "tv" else Anime
                existing = await db.scalar(select(model).where(model.user_id == current_user.id, model.deleted_at.is_(None), func.lower(model.source) == group.source.lower(), model.external_id == group.media_id))
            if existing is not None: skipped[key] += 1; continue
            async with db.begin_nested():
                db.add(item); await db.flush()
                if group.media_type != "movie":
                    seasons = getattr(item, "seasons", []); seasons_created += len(seasons); episodes_created += sum(len(s.episodes) for s in seasons)
                created[key] += 1
        except Exception as exc:
            skipped[key] += 1; errors.append(f"{(group.parent or {}).get('title', group.media_id)}: {exc}")
    await db.commit()
    return YamtrackImportResult(created=created, skipped=skipped, total_rows=len(groups), total_items=len(groups), seasons_created=seasons_created, episodes_created=episodes_created, errors=errors[:30])
