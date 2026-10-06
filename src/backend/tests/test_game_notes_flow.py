"""Notes through the real routes: details, versions, duplicate, move, search,
and the page settings and content counts that sit beside them."""

import os
import uuid
from types import SimpleNamespace

from fastapi import Response

from src.api.routes import games, library_sync
from src.api.schemas.game import GameCreate
from src.database.session import SessionLocal
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


async def _write(flow, name: str, content: str) -> dict:
    response = await flow.client.post(f"{flow.game}/notes/{name}", json={"content": content})
    assert response.status_code == 201, response.text
    return response.json()


async def _summaries(flow) -> dict[str, dict]:
    listed = await flow.client.get(f"{flow.game}/notes-summary")
    assert listed.status_code == 200, listed.text
    return {n["name"]: n for n in listed.json()["notes"]}


async def _achievement(flow) -> str:
    async with SessionLocal() as db:
        await library_sync._replace_achievements(
            db,
            flow.game_id,
            "Steam",
            [
                {
                    "external_id": "A1",
                    "name": "Defeat Margit",
                    "description": None,
                    "icon_url": None,
                    "unlocked": True,
                    "unlocked_at": 1700000000,
                }
            ],
        )
        await db.commit()
    listed = await flow.client.get(f"{flow.game}/achievements")
    return listed.json()[0]["id"]


async def test_note_details_checklist_and_created_date(flow) -> None:
    await _write(flow, "Boss tips", "# Margit\n- [x] summon\n- [ ] dodge\n- [ ] punish\n")
    notes = await _summaries(flow)
    tips = notes["Boss tips"]
    assert tips["created_at"] > 0 and tips["pinned"] is False and tips["tags"] == []
    assert (tips["tasks_done"], tips["tasks_total"]) == (1, 3)

    # an older note with no details row yet gets one, dated by its file
    folder = flow.tmp / str(flow.user_id) / "games" / "Flow" / "notes"
    (folder / "Old.md").write_text("from before", encoding="utf-8")
    os.utime(folder / "Old.md", (1_600_000_000, 1_600_000_000))
    assert (await _summaries(flow))["Old"]["created_at"] == 1_600_000_000

    achievement = await _achievement(flow)
    patched = await flow.client.patch(
        f"{flow.game}/notes/Boss tips/details",
        json={
            "pinned": True,
            "tags": ["boss", " Boss ", "route"],
            "linked_achievement_id": achievement,
        },
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["pinned"] is True and body["tags"] == ["boss", "route"]
    assert body["linked_achievement_id"] == achievement

    # a made-up achievement id is refused
    bad = await flow.client.patch(
        f"{flow.game}/notes/Boss tips/details", json={"linked_achievement_id": str(uuid.uuid4())}
    )
    assert bad.status_code == 404

    cleared = await flow.client.patch(
        f"{flow.game}/notes/Boss tips/details", json={"linked_achievement_id": None}
    )
    assert cleared.json()["linked_achievement_id"] is None
    assert cleared.json()["pinned"] is True  # untouched by the other change

    # renaming keeps the details
    renamed = await flow.client.patch(
        f"{flow.game}/notes/Boss tips/rename", json={"new_name": "Margit"}
    )
    assert renamed.status_code == 200
    assert (await _summaries(flow))["Margit"]["tags"] == ["boss", "route"]


async def test_versions_keep_what_an_edit_replaced_and_can_be_restored(flow) -> None:
    await _write(flow, "Build", "version one")
    for text in ("version two", "version three", "version three"):  # the repeat changes nothing
        saved = await flow.client.put(f"{flow.game}/notes/Build", json={"content": text})
        assert saved.status_code == 200, saved.text
    versions = (await flow.client.get(f"{flow.game}/notes/Build/versions")).json()["versions"]
    assert [v["preview"] for v in versions] == ["version two", "version one"]

    old = versions[-1]
    shown = await flow.client.get(f"{flow.game}/notes/Build/versions/{old['id']}")
    assert shown.json()["content"] == "version one"

    restored = await flow.client.post(f"{flow.game}/notes/Build/versions/{old['id']}/restore")
    assert restored.status_code == 200, restored.text
    assert (await flow.client.get(f"{flow.game}/notes/Build")).text == "version one"
    # what was there before the restore is itself a version now, so it can be undone
    after = (await flow.client.get(f"{flow.game}/notes/Build/versions")).json()["versions"]
    assert "version three" in [v["preview"] for v in after]


async def test_duplicate_move_search_and_delete(flow) -> None:
    await _write(flow, "Route", "Go north to the Church of Elleh, then Limgrave")
    await flow.client.patch(f"{flow.game}/notes/Route/details", json={"tags": ["route"]})

    copy = await flow.client.post(f"{flow.game}/notes/Route/duplicate")
    assert copy.status_code == 201, copy.text
    assert copy.json()["name"] == "Route copy" and copy.json()["tags"] == ["route"]
    again = await flow.client.post(f"{flow.game}/notes/Route/duplicate")
    assert again.json()["name"] == "Route copy 2"

    async with SessionLocal() as db:
        other = await games.create_game(
            GameCreate(title="Other Game", folder_location="Other"),
            Response(),
            db,
            SimpleNamespace(id=flow.user_id),
        )
    moved = await flow.client.post(
        f"{flow.game}/notes/Route/move", json={"target_game_id": str(other.id)}
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["game_title"] == "Other Game"
    assert "Route" not in await _summaries(flow)
    there = (await flow.client.get(f"/api/game/{other.id}/notes-summary")).json()["notes"]
    assert [(n["name"], n["tags"]) for n in there] == [("Route", ["route"])]
    same = await flow.client.post(
        f"/api/game/{other.id}/notes/Route/move", json={"target_game_id": str(other.id)}
    )
    assert same.status_code == 400

    # search spans every game, and finds a note by its text or its name
    by_text = (
        await flow.client.get("/api/game/notes/search", params={"q": "church of elleh"})
    ).json()
    found = {(n["game_title"], n["name"]) for n in by_text["notes"]}
    # the moved note and the two copies all say it
    assert found == {("Other Game", "Route"), ("Flow", "Route copy"), ("Flow", "Route copy 2")}
    assert all("Church of Elleh" in n["snippet"] for n in by_text["notes"])
    by_name = (await flow.client.get("/api/game/notes/search", params={"q": "route copy"})).json()
    assert {n["name"] for n in by_name["notes"]} == {"Route copy", "Route copy 2"}

    gone = await flow.client.delete(f"{flow.game}/notes/Route copy")
    assert gone.status_code == 200
    assert "Route copy" not in await _summaries(flow)


async def test_page_settings_and_content_counts(flow) -> None:
    counts = (await flow.client.get(f"{flow.game}/content-counts")).json()
    assert counts == {
        "achievements": 0,
        "screenshots": 0,
        "clips": 0,
        "soundtrack": 0,
        "saves": 0,
        "worlds": 0,
        "docs": 0,
        "notes": 0,
    }
    await _write(flow, "A note", "text")
    await flow.client.post(
        f"{flow.game}/files/doc", files=[("files", ("guide.pdf", b"%PDF", "application/pdf"))]
    )
    after = (await flow.client.get(f"{flow.game}/content-counts")).json()
    assert (after["notes"], after["docs"]) == (1, 1)

    update = f"/api/game/update/{flow.game_id}"
    ok = await flow.client.patch(
        update,
        json={"page_settings": {"tabs": {"Saves": "hide", "Docs": "auto"}, "hide_rating": True}},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["page_settings"] == {
        "tabs": {"Saves": "hide", "Docs": "auto"},
        "hide_rating": True,
    }

    for bad in (
        {"tabs": {"Overview": "hide"}},
        {"tabs": {"Saves": "sometimes"}},
        {"default_tab": "Nowhere"},
        {"hide_rating": "yes"},
        {"surprise": True},
    ):
        refused = await flow.client.patch(update, json={"page_settings": bad})
        assert refused.status_code == 422, bad

    cleared = await flow.client.patch(update, json={"page_settings": {}})
    assert cleared.status_code == 200 and cleared.json()["page_settings"] is None
