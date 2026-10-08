"""Folder names given to games a library sync creates."""

import uuid

import pytest
from sqlalchemy import delete

from src.api.routes.library_sync import _unique_folder_location
from src.database.models.game import FOLDER_NAME_MAX_LENGTH, Game, GameStatus
from src.database.models.user import User
from src.database.session import SessionLocal


@pytest.fixture
async def two_users():
    ids = []
    async with SessionLocal() as db:
        for _ in range(2):
            user = User(
                username=f"t_{uuid.uuid4().hex[:10]}",
                email=f"{uuid.uuid4().hex[:10]}@example.test",
                password_hash="x",
            )
            db.add(user)
            await db.flush()
            ids.append(user.id)
        await db.commit()
    yield ids
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id.in_(ids)))
        await db.commit()


async def _add_game(user_id, folder: str) -> None:
    async with SessionLocal() as db:
        db.add(
            Game(
                user_id=user_id,
                title=folder[:150],
                sort_title=folder[:150].lower(),
                folder_location=folder,
                status=GameStatus.BACKLOG,
            )
        )
        await db.commit()


async def test_a_taken_long_name_still_fits_the_column(two_users) -> None:
    long_title = "A" * 150
    await _add_game(two_users[0], long_title)
    async with SessionLocal() as db:
        folder = await _unique_folder_location(db, two_users[0], long_title)
    assert len(folder) <= FOLDER_NAME_MAX_LENGTH
    assert folder.endswith("-2")


async def test_another_users_folder_does_not_count(two_users) -> None:
    await _add_game(two_users[0], "Half-Life-2")
    async with SessionLocal() as db:
        folder = await _unique_folder_location(db, two_users[1], "Half-Life 2")
    assert folder == "Half-Life-2"


async def test_one_sync_gives_two_same_named_games_their_own_folders(two_users) -> None:
    from src.helpers.library_games import LibraryIndex, get_or_create_game

    user_id = two_users[0]
    await _add_game(user_id, "Prey")  # an older one, now in another source
    async with SessionLocal() as db:
        index = await LibraryIndex.load(db, user_id, "Steam")
        first, created_first = await get_or_create_game(
            db, user_id, "Prey", "Steam", external_id="480490", index=index
        )
        second, created_second = await get_or_create_game(
            db, user_id, "Prey", "Steam", external_id="6910", index=index
        )
        again, created_again = await get_or_create_game(
            db, user_id, "Prey", "Steam", external_id="480490", index=index
        )
        await db.commit()
    assert created_first and created_second and not created_again
    assert again.id == first.id
    assert {first.folder_location, second.folder_location} == {"Prey-2", "Prey-3"}


async def test_the_index_matches_like_the_database(two_users) -> None:
    from src.helpers.library_games import LibraryIndex, get_or_create_game

    user_id = two_users[0]
    async with SessionLocal() as db:
        # added by hand, no id yet: a synced game with this title claims it
        manual, _ = await get_or_create_game(db, user_id, "Hades", "Steam")
        await db.commit()
        index = await LibraryIndex.load(db, user_id, "Steam")
        synced, created = await get_or_create_game(
            db, user_id, "Hades", "Steam", external_id="1145360", index=index
        )
        assert (synced.id, created) == (manual.id, False)
        assert synced.external_id == "1145360"
        # renamed by the store: still the same game, found by its id
        renamed, created = await get_or_create_game(
            db, user_id, "Hades GOTY", "Steam", external_id="1145360", index=index
        )
        assert (renamed.id, created, renamed.title) == (manual.id, False, "Hades GOTY")
        await db.commit()
