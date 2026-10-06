"""What sits around a game's markdown notes: their details rows, their saved
versions, and the small calculations the Notes tab shows (checklist progress,
a preview). The notes themselves stay files; nothing here writes them."""

from __future__ import annotations

import re
import time
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.game_note_detail import GameNoteDetail, GameNoteVersion

# the newest this many earlier states of a note are kept
MAX_VERSIONS = 30
MAX_TAGS = 20

_TASK = re.compile(r"^\s*[-*+]\s+\[( |x|X)\]\s", re.MULTILINE)


def task_counts(text: str) -> tuple[int, int]:
    """(done, total) for the "- [ ]" and "- [x]" lines in a note."""
    marks = _TASK.findall(text)
    return sum(1 for m in marks if m != " "), len(marks)


def clean_tags(tags: list[str]) -> list[str]:
    seen: list[str] = []
    for tag in tags:
        tag = " ".join(tag.split())[:40]
        if tag and tag.lower() not in {t.lower() for t in seen}:
            seen.append(tag)
    return seen[:MAX_TAGS]


async def ensure_row(
    db: AsyncSession, game_id: UUID, name: str, created_at: int | None = None
) -> GameNoteDetail:
    row = await db.scalar(
        select(GameNoteDetail).where(GameNoteDetail.game_id == game_id, GameNoteDetail.name == name)
    )
    if row is None:
        row = GameNoteDetail(
            game_id=game_id, name=name, created_at=created_at or int(time.time()), tags=[]
        )
        db.add(row)
        await db.flush()
    return row


async def sync_rows(db: AsyncSession, game_id: UUID, notes_dir: Path) -> dict[str, GameNoteDetail]:
    """One row per note file. Notes written before this existed get a row whose
    created date is the file's modified date, the best that can be known; rows
    whose file is gone are dropped (a note deleted or moved outside the app)."""
    paths = (
        {p.stem: p for p in notes_dir.iterdir() if p.is_file() and p.suffix.lower() == ".md"}
        if notes_dir.exists()
        else {}
    )
    rows = {
        r.name: r
        for r in (
            await db.scalars(select(GameNoteDetail).where(GameNoteDetail.game_id == game_id))
        ).all()
    }
    changed = False
    for name, path in paths.items():
        if name not in rows:
            try:
                created = int(path.stat().st_mtime)
            except OSError:
                created = int(time.time())
            row = GameNoteDetail(game_id=game_id, name=name, created_at=created, tags=[])
            db.add(row)
            rows[name] = row
            changed = True
    for name in [n for n in rows if n not in paths]:
        await db.delete(rows.pop(name))
        changed = True
    if changed:
        await db.commit()
    return rows


async def record_version(db: AsyncSession, row: GameNoteDetail, previous_text: str) -> None:
    """Keep the text an edit is about to replace, unless it is the same as the
    newest saved version already."""
    newest = await db.scalar(
        select(GameNoteVersion)
        .where(GameNoteVersion.note_id == row.id)
        .order_by(GameNoteVersion.saved_at.desc(), GameNoteVersion.id)
        .limit(1)
    )
    if newest is not None and newest.content == previous_text:
        return
    # milliseconds, so two saves in the same second still order correctly
    db.add(
        GameNoteVersion(note_id=row.id, content=previous_text, saved_at=int(time.time() * 1000))
    )
    await db.flush()
    keep = (
        await db.scalars(
            select(GameNoteVersion.id)
            .where(GameNoteVersion.note_id == row.id)
            .order_by(GameNoteVersion.saved_at.desc(), GameNoteVersion.id)
            .limit(MAX_VERSIONS)
        )
    ).all()
    await db.execute(
        delete(GameNoteVersion).where(
            GameNoteVersion.note_id == row.id, GameNoteVersion.id.not_in(keep)
        )
    )


async def rename_row(db: AsyncSession, game_id: UUID, old: str, new: str) -> None:
    row = await db.scalar(
        select(GameNoteDetail).where(GameNoteDetail.game_id == game_id, GameNoteDetail.name == old)
    )
    if row is not None:
        row.name = new


async def delete_row(db: AsyncSession, game_id: UUID, name: str) -> None:
    await db.execute(
        delete(GameNoteDetail).where(
            GameNoteDetail.game_id == game_id, GameNoteDetail.name == name
        )
    )
