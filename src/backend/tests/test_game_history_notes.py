"""What the game page's history records, and the note summaries behind the
Notes tab. Uses the real test database; the scratch user is deleted after."""

import uuid
from decimal import Decimal
from types import SimpleNamespace

from fastapi import Response
from sqlalchemy import delete

from src.api.routes import games
from src.api.schemas.game import GameCreate, GameUpdate
from src.database.models.game import GameStatus
from src.database.models.user import User
from src.database.session import SessionLocal


def test_history_values_are_stable_text() -> None:
    text = games._field_change_value_to_text
    assert text(GameStatus.PLAYING) == "PLAYING"
    # the same price written two ways is not a change
    assert text(Decimal("59.90"), "purchase_price") == text(59.9, "purchase_price") == "59.9"
    assert text(Decimal("60.00"), "purchase_price") == "60"
    assert text(1778803200, "purchase_date") == "2026-05-15"
    assert text(["a", "b"]) == "a, b" and text([]) is None and text(None) is None


async def _scratch():
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.commit()
        return user.id


async def test_status_and_price_changes_are_recorded(monkeypatch) -> None:
    monkeypatch.setattr(games, "create_game_folder", lambda *_a: None)
    user_id = await _scratch()
    try:
        owner = SimpleNamespace(id=user_id)
        async with SessionLocal() as db:
            game = await games.create_game(
                GameCreate(
                    title="History", folder_location="History", purchase_price=Decimal("59.90")
                ),
                Response(),
                db,
                owner,
            )
            await games.update_game(
                game.id,
                GameUpdate(
                    status=GameStatus.PLAYING,
                    purchase_price=Decimal("59.9"),
                    purchase_date=1778803200,
                ),
                db,
                owner,
            )
            await games.update_game(game.id, GameUpdate(purchase_price=Decimal("39.99")), db, owner)
            changes = await games.list_field_changes(game.id, db, owner)
        seen = {(c.field_name, c.old_value, c.new_value) for c in changes}
        assert ("status", "BACKLOG", "PLAYING") in seen
        assert ("purchase_date", None, "2026-05-15") in seen
        assert ("purchase_price", "59.9", "39.99") in seen
        # 59.90 written as 59.9 is no change at all
        assert [c for c in changes if c.field_name == "purchase_price"][0].old_value == "59.9"
        assert len([c for c in changes if c.field_name == "purchase_price"]) == 1
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(User).where(User.id == user_id))
            await db.commit()


async def test_note_summaries_carry_edit_time_length_and_preview(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(games, "_DATA_ROOT", tmp_path)
    monkeypatch.setattr(games, "create_game_folder", lambda *_a: None)
    user_id = await _scratch()
    try:
        owner = SimpleNamespace(id=user_id)
        async with SessionLocal() as db:
            game = await games.create_game(
                GameCreate(title="Notes", folder_location="Notes"), Response(), db, owner
            )
            notes = tmp_path / str(user_id) / "games" / "Notes" / "notes"
            notes.mkdir(parents=True)
            (notes / "Boss tips.md").write_text(
                "# Margit\nDodge late.\n" + "word " * 200, encoding="utf-8"
            )
            (notes / "Build.md").write_text("Strength build", encoding="utf-8")
            (notes / "ignore.txt").write_text("not a note", encoding="utf-8")
            out = await games.list_game_note_summaries(game.id, db, owner)
        names = [n["name"] for n in out["notes"]]
        assert names == ["Boss tips", "Build"]
        tips = out["notes"][0]
        assert tips["words"] == 204 and tips["updated_at"] > 0
        assert tips["preview"].startswith("# Margit") and len(tips["preview"]) == 600
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(User).where(User.id == user_id))
            await db.commit()
