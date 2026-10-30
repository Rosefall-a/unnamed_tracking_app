"""Bulk delete moves only the caller's own live games to the trash."""

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select

from src.api.routes import games
from src.api.schemas.game import GameBulkDelete
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import SessionLocal


@pytest.fixture
def trashed_folders(monkeypatch):
    moved: list[uuid.UUID] = []
    monkeypatch.setattr(games, "move_game_to_trash", lambda _path, _root, game_id: moved.append(game_id))
    return moved


async def _make_user_with_games(count: int) -> tuple[uuid.UUID, list[uuid.UUID]]:
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.flush()
        rows = [
            Game(user_id=user.id, title=f"Game {i}", sort_title=f"game {i}", folder_location=f"game_{i}")
            for i in range(count)
        ]
        db.add_all(rows)
        await db.commit()
        return user.id, [row.id for row in rows]


async def _drop_user(user_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def _deleted_flags(game_ids: list[uuid.UUID]) -> list[bool]:
    async with SessionLocal() as db:
        rows = (await db.execute(select(Game).where(Game.id.in_(game_ids)))).scalars().all()
        by_id = {row.id: row.deleted_at is not None for row in rows}
        return [by_id[game_id] for game_id in game_ids]


async def test_bulk_delete_trashes_selected_games_only(trashed_folders):
    user_id, game_ids = await _make_user_with_games(3)
    try:
        async with SessionLocal() as db:
            result = await games.bulk_delete_games(
                GameBulkDelete(game_ids=game_ids[:2]), db, SimpleNamespace(id=user_id)
            )
        assert result == {"deleted": 2}
        assert await _deleted_flags(game_ids) == [True, True, False]
        assert trashed_folders == game_ids[:2]
    finally:
        await _drop_user(user_id)


async def test_bulk_delete_skips_other_users_and_already_trashed_games(trashed_folders):
    owner_id, owner_games = await _make_user_with_games(2)
    other_id, other_games = await _make_user_with_games(1)
    try:
        async with SessionLocal() as db:
            await games.bulk_delete_games(
                GameBulkDelete(game_ids=[owner_games[0]]), db, SimpleNamespace(id=owner_id)
            )
        async with SessionLocal() as db:
            result = await games.bulk_delete_games(
                GameBulkDelete(game_ids=[*owner_games, *other_games]),
                db,
                SimpleNamespace(id=owner_id),
            )
        assert result == {"deleted": 1}
        assert await _deleted_flags(other_games) == [False]
        assert trashed_folders == owner_games
    finally:
        await _drop_user(owner_id)
        await _drop_user(other_id)


async def test_a_failed_folder_move_leaves_files_in_place_and_others_still_move(monkeypatch):
    user_id, game_ids = await _make_user_with_games(2)
    moved: list[uuid.UUID] = []

    def flaky_move(_path, _root, game_id):
        if game_id == game_ids[0]:
            raise OSError("disk busy")
        moved.append(game_id)

    monkeypatch.setattr(games, "move_game_to_trash", flaky_move)
    try:
        async with SessionLocal() as db:
            result = await games.bulk_delete_games(
                GameBulkDelete(game_ids=game_ids), db, SimpleNamespace(id=user_id)
            )
        assert result == {"deleted": 2}
        assert await _deleted_flags(game_ids) == [True, True]
        assert moved == [game_ids[1]]
    finally:
        await _drop_user(user_id)
