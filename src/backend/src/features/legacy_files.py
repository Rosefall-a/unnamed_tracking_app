"""Files left in /data/games, the shared folder the app used before each person got
their own under /data/users. Nothing reads it any more, so anything only there no
longer shows up. This finds those files and copies them into the games they belong
to. Originals are never moved or changed, and copying twice adds nothing."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models.game import Game
from src.database.models.game_archive import GameArchive
from src.database.models.game_file_item import GameFileItem
from src.database.models.media_item import MediaItem
from src.features import game_notes
from src.helpers.media_dates import detect_date_of_file
from src.helpers.save_game_asset import DATA_ROOT

LEGACY_ROOT = Path("/data/games")
# the subfolder, and what kind of row a file in it gets
_MEDIA = {"screenshots": "screenshot", "clips": "clip", "soundtrack": "soundtrack"}
_FILES = {"docs": "doc", "modpacks": "modpack"}
_ARCHIVES = {"save": "saves", "world_save": "world_saves"}
_NOTES = "notes"
# rendered map tiles for a feature the app no longer has: too big to copy unasked
_LEFT_ALONE = "world_map"


def _active_dir(game: Game) -> Path:
    return DATA_ROOT / str(game.user_id) / "games" / game.folder_location


def _home(game: Game) -> Path:
    return DATA_ROOT / "_trash" / str(game.id) if game.deleted_at else _active_dir(game)


def _files_in(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and not p.name.startswith("."))


def _same_file(source: Path, target: Path) -> bool:
    return target.is_file() and target.stat().st_size == source.stat().st_size


def _copy(source: Path, target: Path) -> None:
    """All or nothing: a copy cut short never takes the real name."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.part")
    shutil.copy2(source, temporary)
    os.replace(temporary, target)


def _match(games: list[Game], folder: str) -> Game | None:
    """The person's game in this folder, or in the numbered folder a re-import gave
    it ("ELDEN-RING-2"). A game still in the library wins over one in the trash."""
    pattern = re.compile(rf"^{re.escape(folder)}(-\d+)?$")
    found = [g for g in games if g.folder_location and pattern.match(g.folder_location)]
    active = [g for g in found if g.deleted_at is None]
    candidates = active or found
    return candidates[0] if candidates else None


async def _user_games(db: AsyncSession, user_id: UUID) -> list[Game]:
    return list((await db.scalars(select(Game).where(Game.user_id == user_id))).all())


def _legacy_folders() -> list[Path]:
    if not LEGACY_ROOT.is_dir():
        return []
    return sorted(p for p in LEGACY_ROOT.iterdir() if p.is_dir() and p.name != "_trash")


def _missing_from(folder: Path, target_dir: Path) -> list[Path]:
    return [f for f in _files_in(folder) if not _same_file(f, target_dir / f.name)]


async def _missing_versions(db: AsyncSession, game: Game) -> list[tuple[Path, Path]]:
    """Save versions the database lists whose file only exists in the old folder."""
    archives = await db.scalars(
        select(GameArchive)
        .options(selectinload(GameArchive.versions))
        .where(GameArchive.game_id == game.id)
    )
    pairs = []
    for archive in archives.all():
        sub = _ARCHIVES.get(archive.kind)
        if sub is None:
            continue
        for version in archive.versions:
            in_trash = archive.deleted_at is not None or version.deleted_at is not None
            target = (
                _home(game) / "_trash" / archive.kind / str(archive.id) / "files" / version.filename
                if in_trash
                else _home(game) / sub / str(archive.id) / version.filename
            )
            base = re.sub(r"-\d+$", "", game.folder_location)
            for folder in (game.folder_location, base):
                source = LEGACY_ROOT / folder / sub / str(archive.id) / version.filename
                if source.is_file() and not target.is_file():
                    pairs.append((source, target))
                    break
    return pairs


async def scan_old_files(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
    """Read only: what this person could get back."""
    games = await _user_games(db, user_id)
    folders = []
    no_game = []
    for folder in _legacy_folders():
        game = _match(games, folder.name)
        if game is None:
            no_game.append(folder.name)
            continue
        counts: Counter[str] = Counter()
        home = _home(game)
        for sub in (*_MEDIA, *_FILES, _NOTES):
            if game.deleted_at is None or (home / sub).is_dir():
                counts[sub] = len(_missing_from(folder / sub, home / sub))
        counts["saves"] = len(await _missing_versions(db, game))
        counts = +counts
        if counts:
            folders.append(
                {
                    "folder": folder.name,
                    "game_id": str(game.id),
                    "title": game.title,
                    "in_trash": game.deleted_at is not None,
                    "files": dict(counts),
                }
            )
    left_alone = sum(1 for f in _legacy_folders() if (f / _LEFT_ALONE).is_dir())
    return {"folders": folders, "no_game": no_game, "map_folders": left_alone}


async def restore_old_files(db: AsyncSession, user_id: UUID) -> dict[str, int]:
    """Copies everything scan_old_files found. A file that cannot be copied is
    counted and left for another try."""
    games = await _user_games(db, user_id)
    copied = failed = 0
    for folder in _legacy_folders():
        game = _match(games, folder.name)
        if game is None:
            continue
        home = _home(game)
        pending: list[tuple[str, Path, Path]] = []
        for sub, kind in _MEDIA.items():
            pending += [(kind, f, home / sub / f.name) for f in _missing_from(folder / sub, home / sub)]
        for sub, kind in _FILES.items():
            pending += [(kind, f, home / sub / f.name) for f in _missing_from(folder / sub, home / sub)]
        pending += [(_NOTES, f, home / _NOTES / f.name) for f in _missing_from(folder / _NOTES, home / _NOTES)]
        pending += [("saves", s, t) for s, t in await _missing_versions(db, game)]

        known_media = set(
            await db.scalars(select(MediaItem.filename).where(MediaItem.game_id == game.id))
        )
        known_files = set(
            await db.scalars(select(GameFileItem.filename).where(GameFileItem.game_id == game.id))
        )
        for kind, source, target in pending:
            # never over a different file that happens to have the same name
            if target.exists():
                failed += 1
                continue
            try:
                await asyncio.to_thread(_copy, source, target)
            except OSError:
                failed += 1
                continue
            copied += 1
            if kind in _MEDIA.values() and source.name not in known_media:
                taken_at, taken_source = detect_date_of_file(target, source.name, kind)
                db.add(
                    MediaItem(
                        game_id=game.id,
                        kind=kind,
                        filename=source.name,
                        taken_at=taken_at,
                        taken_source=taken_source,
                    )
                )
            elif kind in _FILES.values() and source.name not in known_files:
                db.add(GameFileItem(game_id=game.id, kind=kind, filename=source.name))
            elif kind == _NOTES:
                await game_notes.ensure_row(db, game.id, source.stem)
        await db.commit()
    return {"copied": copied, "failed": failed}
