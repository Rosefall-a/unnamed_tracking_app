"""The game file tabs end to end, through the real routes: soundtrack, clips,
screenshots, docs and saves. Uploads land in a temporary folder, the database
is the real test one, and the scratch user (with its games) is deleted after.
"""

import io
import uuid
from types import SimpleNamespace

import httpx
import pytest
from fastapi import Response
from PIL import Image
from sqlalchemy import delete

from src.api.routes import game_archives, game_notes as game_notes_routes, game_page, games
from src.api.schemas.game import GameCreate
from src.core.auth import get_current_user
from src.database.models.user import User
from src.database.session import SessionLocal
from src.main import app
from tests.test_media_dates import _mp4_with_creation, utc


@pytest.fixture
async def flow(tmp_path, monkeypatch):
    monkeypatch.setattr(games, "_DATA_ROOT", tmp_path)
    monkeypatch.setattr(game_archives, "_DATA_ROOT", tmp_path)
    monkeypatch.setattr(game_notes_routes, "_DATA_ROOT", tmp_path)
    monkeypatch.setattr(game_page, "_DATA_ROOT", tmp_path)
    monkeypatch.setattr(games, "create_game_folder", lambda *_a: None)
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.commit()
        user_id = user.id
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id)
    async with SessionLocal() as db:
        game = await games.create_game(
            GameCreate(title="Flow", folder_location="Flow"),
            Response(),
            db,
            SimpleNamespace(id=user_id),
        )
        game_id = game.id
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield SimpleNamespace(
            client=client, game=f"/api/game/{game_id}", game_id=game_id, user_id=user_id, tmp=tmp_path
        )
    app.dependency_overrides.pop(get_current_user, None)
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4)).save(buffer, "PNG")
    return buffer.getvalue()


async def test_screenshots_clips_and_soundtrack_upload_list_edit_and_detect(flow) -> None:
    clip = _mp4_with_creation(utc(2026, 5, 15, 19, 10, 11))
    response = await flow.client.post(
        f"{flow.game}/screenshots",
        files=[
            ("files", ("20260102_030405_shot.png", _png(), "image/png")),
            ("files", ("render.mp4", clip, "video/mp4")),
            ("files", ("theme.mp3", b"ID3" + b"\x00" * 64, "audio/mpeg")),
            ("files", ("notes.txt", b"hello", "text/plain")),
        ],
        data={"last_modified": ["1700000000000"] * 4},
    )
    assert response.status_code == 200, response.text
    results = response.json()["results"]
    assert [r["status"] for r in results] == ["saved", "saved", "saved", "rejected"]
    assert [r.get("kind") for r in results[:3]] == ["screenshot", "clip", "soundtrack"]

    listed = (await flow.client.get(f"{flow.game}/screenshots")).json()["media"]
    by_kind = {m["kind"]: m for m in listed}
    assert by_kind["screenshot"]["taken_source"] == "filename"
    assert by_kind["screenshot"]["taken_at"] == utc(2026, 1, 2, 3, 4, 5)
    assert by_kind["clip"]["taken_source"] == "video"
    assert by_kind["clip"]["taken_at"] == utc(2026, 5, 15, 19, 10, 11)
    # no date in the file or its name: falls back to the modified date sent with it
    assert by_kind["soundtrack"]["taken_source"] == "file"
    assert by_kind["soundtrack"]["taken_at"] == 1700000000

    track = by_kind["soundtrack"]
    edited = await flow.client.patch(
        f"{flow.game}/screenshots/{track['id']}",
        json={"title": "Main theme", "note": "Plays at the start", "tags": ["ost"], "taken_at": utc(2025, 12, 25)},
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert (body["title"], body["note"], body["tags"]) == ("Main theme", "Plays at the start", ["ost"])
    assert (body["taken_at"], body["taken_source"]) == (utc(2025, 12, 25), "manual")

    from_achievement = await flow.client.patch(
        f"{flow.game}/screenshots/{track['id']}",
        json={"taken_at": utc(2026, 6, 2, 9, 0), "taken_source": "achievement"},
    )
    assert from_achievement.json()["taken_source"] == "achievement"

    # detect: the clip and screenshot carry dates; the track does not
    detected = await flow.client.post(
        f"{flow.game}/screenshots/detect-dates", json={"ids": [m["id"] for m in listed]}
    )
    assert detected.status_code == 200, detected.text
    assert {m["kind"] for m in detected.json()["media"]} == {"screenshot", "clip"}

    # partial requests work, which is what makes a clip's length and seeking correct
    clip_url = by_kind["clip"]["url"]
    ranged = await flow.client.get(clip_url, headers={"Range": "bytes=0-9"})
    assert ranged.status_code == 206
    assert ranged.headers["content-range"].startswith("bytes 0-9/")
    assert len(ranged.content) == 10

    # delete goes to the trash and can be restored
    gone = await flow.client.delete(f"{flow.game}/screenshots/soundtrack/{track['filename']}")
    assert gone.status_code == 200
    trash = (await flow.client.get(f"{flow.game}/screenshots/trash")).json()["media"]
    assert [t["filename"] for t in trash] == [track["filename"]]
    restored = await flow.client.post(
        f"{flow.game}/screenshots/soundtrack/{track['filename']}/restore"
    )
    assert restored.status_code == 200
    assert restored.json()["title"] == "Main theme"  # details survive the trash


async def test_docs_upload_edit_delete_and_restore(flow) -> None:
    response = await flow.client.post(
        f"{flow.game}/files/doc",
        files=[
            ("files", ("Boss Guide 2026-03-02.pdf", b"%PDF-1.4 guide", "application/pdf")),
            ("files", ("map.zip", b"PK\x03\x04", "application/zip")),
        ],
        data={"last_modified": ["1700000000000", "1700000000000"]},
    )
    assert response.status_code == 200, response.text
    assert [r["status"] for r in response.json()["results"]] == ["saved", "saved"]

    files = (await flow.client.get(f"{flow.game}/files/doc")).json()["files"]
    by_name = {f["filename"].split("_", 1)[1]: f for f in files}
    guide = by_name["Boss_Guide_2026-03-02.pdf"]
    assert guide["taken_source"] == "filename" and guide["taken_at"] == utc(2026, 3, 2)
    assert by_name["map.zip"]["taken_source"] == "file"
    assert guide["size"] == len(b"%PDF-1.4 guide") and guide["id"]

    patched = await flow.client.patch(
        f"{flow.game}/files/doc/by-id/{guide['id']}",
        json={"title": "Elden Ring boss guide", "note": "Pages 4 to 9", "tags": ["guide", "bosses"], "taken_at": utc(2026, 4, 1)},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["title"] == "Elden Ring boss guide"
    assert patched.json()["tags"] == ["guide", "bosses"]
    assert patched.json()["taken_source"] == "manual"

    # an id from another kind of file is not found
    wrong = await flow.client.patch(
        f"{flow.game}/files/modpack/by-id/{guide['id']}", json={"title": "x"}
    )
    assert wrong.status_code == 404

    deleted = await flow.client.delete(f"{flow.game}/files/doc/{guide['filename']}")
    assert deleted.status_code == 200
    trash = (await flow.client.get(f"{flow.game}/files/doc/trash")).json()["files"]
    assert len(trash) == 1 and trash[0]["id"] == guide["id"]
    assert [f["filename"] for f in (await flow.client.get(f"{flow.game}/files/doc")).json()["files"]] == [
        by_name["map.zip"]["filename"]
    ]

    restored = await flow.client.post(f"{flow.game}/files/doc/{guide['filename']}/restore")
    assert restored.status_code == 200, restored.text
    again = {f["id"]: f for f in (await flow.client.get(f"{flow.game}/files/doc")).json()["files"]}
    assert again[guide["id"]]["title"] == "Elden Ring boss guide"


async def test_saves_are_named_archives_with_versions(flow) -> None:
    created = await flow.client.post(
        f"{flow.game}/archives/save",
        data={"name": "Main character"},
        files={"file": ("slot1.sav", b"v1" * 10, "application/octet-stream")},
    )
    assert created.status_code == 200, created.text
    archive = created.json()
    assert archive["name"] == "Main character" and len(archive["versions"]) == 1

    more = await flow.client.post(
        f"{flow.game}/archives/{archive['id']}/versions",
        files={"file": ("slot1.sav", b"v2" * 20, "application/octet-stream")},
    )
    assert more.status_code == 200, more.text
    assert len(more.json()["versions"]) == 2

    renamed = await flow.client.patch(
        f"{flow.game}/archives/{archive['id']}", json={"name": "Before the final boss"}
    )
    assert renamed.json()["name"] == "Before the final boss"

    listed = (await flow.client.get(f"{flow.game}/archives/save")).json()
    assert [a["name"] for a in listed] == ["Before the final boss"]

    assert (await flow.client.delete(f"{flow.game}/archives/{archive['id']}")).status_code in (200, 204)
    trash = (await flow.client.get(f"{flow.game}/archives/save/trash")).json()
    assert [t["name"] for t in trash] == ["Before the final boss"]
    restored = await flow.client.post(f"{flow.game}/archives/{archive['id']}/restore")
    assert restored.status_code == 200, restored.text
    assert len((await flow.client.get(f"{flow.game}/archives/save")).json()) == 1


async def test_a_clip_keeps_its_thumbnail_and_length(flow) -> None:
    from tests.test_media_dates import _mp4_with_creation, utc

    clip = _mp4_with_creation(utc(2026, 5, 15, 19, 10, 11))
    uploaded = await flow.client.post(
        f"{flow.game}/screenshots", files=[("files", ("run.mp4", clip, "video/mp4"))]
    )
    assert uploaded.status_code == 200, uploaded.text
    media = (await flow.client.get(f"{flow.game}/screenshots")).json()["media"]
    item = media[0]
    assert item["thumbnail_url"] is None and item["duration"] is None

    # a wide picture is stored shrunk to 640 across, as a JPEG
    wide = io.BytesIO()
    Image.new("RGB", (1920, 1080), (200, 100, 20)).save(wide, "PNG")
    saved = await flow.client.post(
        f"{flow.game}/thumbnails/{item['id']}",
        files={"file": ("frame.png", wide.getvalue(), "image/png")},
        data={"duration": "93.5"},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["duration"] == 93.5
    assert saved.json()["thumbnail_url"] == f"{flow.game}/thumbnails/{item['id']}"

    shown = await flow.client.get(saved.json()["thumbnail_url"])
    assert shown.status_code == 200 and shown.headers["content-type"] == "image/jpeg"
    assert "immutable" in shown.headers["cache-control"]
    with Image.open(io.BytesIO(shown.content)) as picture:
        assert picture.size == (640, 360)

    # the list now carries both, so nothing has to load the video to show them
    again = (await flow.client.get(f"{flow.game}/screenshots")).json()["media"][0]
    assert again["thumbnail_url"] and again["duration"] == 93.5

    refused = await flow.client.post(
        f"{flow.game}/thumbnails/{item['id']}",
        files={"file": ("frame.png", b"not a picture", "image/png")},
    )
    assert refused.status_code == 400
    # only clips have thumbnails
    png = io.BytesIO()
    Image.new("RGB", (4, 4)).save(png, "PNG")
    await flow.client.post(
        f"{flow.game}/screenshots", files=[("files", ("shot.png", png.getvalue(), "image/png"))]
    )
    shot = [m for m in (await flow.client.get(f"{flow.game}/screenshots")).json()["media"] if m["kind"] == "screenshot"][0]
    wrong = await flow.client.post(
        f"{flow.game}/thumbnails/{shot['id']}", files={"file": ("f.png", png.getvalue(), "image/png")}
    )
    assert wrong.status_code == 404
