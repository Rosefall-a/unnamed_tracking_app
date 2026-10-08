"""Finding the game a library sync is about, or creating it with a folder of
its own: matched by the provider's id when it has one, else by title."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.game import FOLDER_NAME_MAX_LENGTH, Game, GameStatus
from src.helpers.save_game_asset import create_game_folder

_SLUG_INVALID = re.compile(r"[^A-Za-z0-9_-]+")


def slugify(title: str) -> str:
    slug = _SLUG_INVALID.sub("-", title).strip("-")
    return slug or "game"


def _folder_candidates(title: str) -> Iterator[str]:
    """The title's folder name, then "-2", "-3"... cut to fit the column (a
    150-character title with a suffix used to fail the insert)."""
    base = slugify(title)[:FOLDER_NAME_MAX_LENGTH]
    yield base
    suffix = 2
    while True:
        tail = f"-{suffix}"
        yield f"{base[: FOLDER_NAME_MAX_LENGTH - len(tail)]}{tail}"
        suffix += 1


async def unique_folder_location(db: AsyncSession, user_id: UUID, title: str) -> str:
    """A folder name none of the user's games has (trashed ones keep theirs)."""
    taken = select(Game.id).where(Game.user_id == user_id)
    for candidate in _folder_candidates(title):
        if await db.scalar(taken.where(Game.folder_location == candidate)) is None:
            return candidate
    raise AssertionError("unreachable")


@dataclass
class LibraryIndex:
    """One source's games of one user and every folder name the user has,
    read once for a whole sync. Without it a sync asked the database about
    each game it saw (one or two queries a game, and another for each new
    game's folder name): about 2,000 queries for a 1,000-game library."""

    by_external: dict[str, Game] = field(default_factory=dict)
    by_title: dict[str, list[Game]] = field(default_factory=dict)
    folders: set[str] = field(default_factory=set)

    @classmethod
    async def load(cls, db: AsyncSession, user_id: UUID, source: str) -> LibraryIndex:
        index = cls()
        games = await db.scalars(
            select(Game).where(
                Game.user_id == user_id, Game.source == source, Game.deleted_at.is_(None)
            )
        )
        for game in games:
            index.add(game)
        index.folders = set(
            await db.scalars(select(Game.folder_location).where(Game.user_id == user_id))
        )
        return index

    def add(self, game: Game) -> None:
        if game.external_id:
            self.by_external.setdefault(game.external_id, game)
        self.by_title.setdefault(game.title, []).append(game)
        self.folders.add(game.folder_location)

    def find(self, title: str, external_id: str | None) -> Game | None:
        """The same choice the database lookups make: the game with this id,
        else one with this title (that has no id of its own, when the synced
        game has one: Prey 2006 and Prey 2017 share a name)."""
        if external_id and external_id in self.by_external:
            return self.by_external[external_id]
        return next(
            (g for g in self.by_title.get(title, []) if not external_id or not g.external_id),
            None,
        )

    def retitle(self, game: Game, title: str) -> None:
        same = self.by_title.get(game.title, [])
        if game in same:
            same.remove(game)
        self.by_title.setdefault(title, []).append(game)

    def claim_folder(self, title: str) -> str:
        folder = next(c for c in _folder_candidates(title) if c not in self.folders)
        self.folders.add(folder)
        return folder


async def _find(
    db: AsyncSession, user_id: UUID, title: str, source: str, external_id: str | None
) -> Game | None:
    if external_id:
        found = await db.scalar(
            select(Game).where(
                Game.user_id == user_id,
                Game.source == source,
                Game.external_id == external_id,
                Game.deleted_at.is_(None),
            )
        )
        if found is not None:
            return found
    by_title = select(Game).where(
        Game.user_id == user_id,
        Game.source == source,
        Game.title == title,
        Game.deleted_at.is_(None),
    )
    if external_id:
        # two different games can share a name (Prey 2006 and Prey 2017); one
        # that has its own id is not the game being synced
        by_title = by_title.where(Game.external_id.is_(None))
    return await db.scalar(by_title.limit(1))


async def get_or_create_game(
    db: AsyncSession,
    user_id: UUID,
    title: str,
    source: str,
    external_id: str | None = None,
    index: LibraryIndex | None = None,
) -> tuple[Game, bool]:
    """Match by (user, source, external_id) when the provider gives a
    stable id — a title alone drifts (Steam has reported a different
    display name for the same appid between calls, e.g. briefly appending
    "- GOTY Edition"), which was creating duplicate rows for one real game.
    Falls back to matching by (user, source, title) when no id is given.
    A sync touching many games passes its LibraryIndex (see above)."""
    if index is not None:
        existing = index.find(title, external_id)
    else:
        existing = await _find(db, user_id, title, source, external_id)
    if existing:
        if existing.title != title:
            if index is not None:
                index.retitle(existing, title)
            existing.title = title
            existing.sort_title = title.lower()
        if external_id and not existing.external_id:
            existing.external_id = external_id
            if index is not None:
                index.by_external.setdefault(external_id, existing)
        # this sync just saw it again — clear any earlier "missing from your
        # library" flag (see _flag_stale_games)
        existing.stale_since = None
        return existing, False

    if index is not None:
        folder_location = index.claim_folder(title)
    else:
        folder_location = await unique_folder_location(db, user_id, title)
    game = Game(
        user_id=user_id,
        title=title,
        sort_title=title.lower(),
        folder_location=folder_location,
        source=source,
        external_id=external_id,
        status=GameStatus.BACKLOG,
    )
    db.add(game)
    # the insert fills in the id and the column defaults (empty tags...) that
    # callers go on to read
    await db.flush()
    if index is not None:
        index.add(game)
    create_game_folder(user_id, folder_location)
    return game, True
