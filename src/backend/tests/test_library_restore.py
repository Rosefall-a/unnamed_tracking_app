"""Restoring games from an exported file: they come back as the store's games,
importing a file twice does not double the library, and other people's folders
do not get in the way."""

import uuid

from sqlalchemy import delete

from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import SessionLocal
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


def _game(title: str = "Hades", **fields) -> dict:
    return {
        "title": title,
        "folder_location": title.replace(" ", "-"),
        "source": "Steam",
        "external_id": "1145360",
        **fields,
    }


async def test_a_restored_game_keeps_its_store_id_and_is_not_added_twice(flow) -> None:
    first = await flow.client.post("/api/import/library", json=[_game()])
    assert first.json() == {"created": 1, "skipped": 0, "errors": []}

    exported = (await flow.client.get("/api/export/library")).json()["games"]
    restored = next(g for g in exported if g["title"] == "Hades")
    assert restored["external_id"] == "1145360"

    again = await flow.client.post("/api/import/library", json=[restored])
    assert again.json() == {"created": 0, "skipped": 1, "errors": []}


async def test_a_game_with_the_same_name_but_another_id_is_its_own_game(flow) -> None:
    await flow.client.post("/api/import/library", json=[_game("Prey", external_id="480490")])
    other = await flow.client.post("/api/import/library", json=[_game("Prey", external_id="111")])
    assert other.json()["created"] == 1
    exported = (await flow.client.get("/api/export/library")).json()["games"]
    folders = sorted(g["folder_location"] for g in exported if g["title"] == "Prey")
    assert folders == ["Prey", "Prey-2"]


async def test_other_peoples_folders_do_not_stop_or_rename_a_restore(flow) -> None:
    others = []
    async with SessionLocal() as db:
        for _ in range(2):
            name = uuid.uuid4().hex[:10]
            user = User(username=f"t_{name}", email=f"{name}@example.test", password_hash="x")
            db.add(user)
            await db.flush()
            others.append(user.id)
            db.add(
                Game(
                    user_id=user.id,
                    title="Shared",
                    sort_title="shared",
                    folder_location="Shared",
                    tags=[],
                    features=[],
                    collections=[],
                )
            )
        await db.commit()
    try:
        result = await flow.client.post("/api/import/library", json=[_game("Shared")])
        assert result.json() == {"created": 1, "skipped": 0, "errors": []}
        exported = (await flow.client.get("/api/export/library")).json()["games"]
        assert next(g for g in exported if g["title"] == "Shared")["folder_location"] == "Shared"
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(User).where(User.id.in_(others)))
            await db.commit()
