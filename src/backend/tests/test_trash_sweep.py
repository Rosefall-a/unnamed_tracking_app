"""Retention checks keep active/recoverable rows and purge expired files."""

import time
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from src.database.models.game import Game
from src.database.models.game_file_item import GameFileItem
from src.database.models.media_item import MediaItem
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features.trash import sweep
from src.main import app  # noqa: F401 — register the complete application model graph


@pytest.mark.asyncio
async def test_trash_sweep_purges_expired_data_and_keeps_recoverable_files(monkeypatch, tmp_path):
    monkeypatch.setattr(sweep, "_DATA_ROOT", tmp_path)
    user_id = uuid4()
    game_ids = {state: uuid4() for state in ("active", "recent", "expired")}
    cutoff = int(time.time()) - sweep.RETENTION_SECONDS
    deleted_at = {"active": None, "recent": cutoff + 60, "expired": cutoff - 60}
    try:
        async with SessionLocal() as db:
            db.add(
                User(
                    id=user_id,
                    username=f"sweep-{user_id}",
                    email=f"{user_id}@example.test",
                    password_hash="unused",
                )
            )
            await db.flush()
            for state, game_id in game_ids.items():
                db.add(
                    Game(
                        id=game_id,
                        user_id=user_id,
                        title=state,
                        sort_title=state,
                        folder_location=state,
                        deleted_at=deleted_at[state],
                    )
                )
            await db.flush()
            for state in deleted_at:
                db.add(
                    MediaItem(
                        game_id=game_ids["active"],
                        kind="screenshot",
                        filename=f"{state}.png",
                        deleted_at=deleted_at[state],
                    )
                )
                db.add(
                    GameFileItem(
                        game_id=game_ids["active"],
                        kind="doc",
                        filename=f"{state}.pdf",
                        deleted_at=deleted_at[state],
                    )
                )
            await db.commit()
        for kind, extension in (("screenshot", "png"), ("doc", "pdf")):
            folder = tmp_path / "active" / "_trash" / kind
            folder.mkdir(parents=True)
            for state in deleted_at:
                (folder / f"{state}.{extension}").write_bytes(b"recoverable data")
        game_trash = tmp_path / "_trash" / str(game_ids["expired"])
        game_trash.mkdir(parents=True)
        (game_trash / "whole-game.txt").write_text("expired", encoding="utf-8")

        result = await sweep.purge_expired_trash()
        assert (
            result["purged_games"]
            == result["purged_media_items"]
            == result["purged_file_items"]
            == 1
        )
        assert not game_trash.exists()
        for kind, extension in (("screenshot", "png"), ("doc", "pdf")):
            folder = tmp_path / "active" / "_trash" / kind
            assert not (folder / f"expired.{extension}").exists()
            assert (folder / f"active.{extension}").is_file()
            assert (folder / f"recent.{extension}").is_file()
        async with SessionLocal() as db:
            remaining_games = set(
                (await db.scalars(select(Game.id).where(Game.user_id == user_id))).all()
            )
            assert remaining_games == {game_ids["active"], game_ids["recent"]}
            media = (
                await db.scalars(
                    select(MediaItem.filename).where(MediaItem.game_id == game_ids["active"])
                )
            ).all()
            docs = (
                await db.scalars(
                    select(GameFileItem.filename).where(GameFileItem.game_id == game_ids["active"])
                )
            ).all()
            assert set(media) == {"active.png", "recent.png"}
            assert set(docs) == {"active.pdf", "recent.pdf"}
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(User).where(User.id == user_id))
            await db.commit()
