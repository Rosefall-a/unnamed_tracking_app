"""Saving a Home layout keeps the one it replaces, so an edit can be undone."""

import uuid

import pytest
from sqlalchemy import delete

from src.core import preferences
from src.database.models.user import User
from src.database.session import SessionLocal


def _layout(note: str, *, widgets: int = 1) -> dict:
    return {
        "version": 1,
        "pages": [
            {
                "id": "home",
                "name": "Home",
                "options": {"gap": "cozy", "backdrop": "glow"},
                "widgets": [
                    {
                        "id": f"note-{i + 1}",
                        "type": "note",
                        "x": 0,
                        "y": i * 3,
                        "w": 4,
                        "h": 3,
                        "settings": {"text": note},
                        "variant": None,
                    }
                    for i in range(widgets)
                ],
            }
        ],
    }


@pytest.fixture
async def user_id():
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.commit()
        uid = user.id
    yield uid
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == uid))
        await db.commit()


async def _save(uid, layout) -> dict:
    async with SessionLocal() as db:
        return await preferences.save_preferences(db, uid, {"home_layout": layout})


async def _history(uid) -> list:
    async with SessionLocal() as db:
        return await preferences.load_home_layout_history(db, uid)


async def test_a_new_arrangement_keeps_the_one_before(user_id) -> None:
    await _save(user_id, _layout("a"))
    assert await _history(user_id) == []  # nothing came before the first
    saved = await _save(user_id, _layout("a", widgets=2))
    history = await _history(user_id)
    assert [len(h["layout"]["pages"][0]["widgets"]) for h in history] == [1]
    assert preferences.HOME_HISTORY_KEY not in saved, "history is never sent with preferences"


async def test_typing_in_a_note_keeps_one_earlier_version_not_one_per_save(user_id) -> None:
    await _save(user_id, _layout("first"))
    for text in ("first e", "first ed", "first edit"):
        await _save(user_id, _layout(text))
    history = await _history(user_id)
    assert [h["layout"]["pages"][0]["widgets"][0]["settings"]["text"] for h in history] == ["first"]


async def test_history_keeps_the_latest_fifteen(user_id) -> None:
    for n in range(1, 20):
        await _save(user_id, _layout("x", widgets=n))
    history = await _history(user_id)
    assert len(history) == 15
    assert len(history[0]["layout"]["pages"][0]["widgets"]) == 18
