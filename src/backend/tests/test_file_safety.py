"""Uploads never leave half a file or an orphan, big files are not held in memory,
names keep their letters, and files stuck in the old shared folder can be brought
back without touching the originals."""

import io
import uuid
from types import SimpleNamespace

import pytest
from fastapi import UploadFile
from PIL import Image
from sqlalchemy import select

from src.database.models.game import Game
from src.database.models.game_archive import GameArchive, GameArchiveVersion
from src.database.models.game_file_item import GameFileItem
from src.database.models.media_item import MediaItem
from src.database.session import SessionLocal
from src.features import legacy_files
from src.features.metadata.games import repair
from src.helpers import game_info_file, save_game_asset
from src.helpers.media import UploadTooLarge, list_media, safe_filename, save_media_bytes, save_upload
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), (10, 20, 30)).save(buffer, "PNG")
    return buffer.getvalue()


async def test_a_too_big_upload_leaves_nothing_behind(tmp_path) -> None:
    upload = UploadFile(io.BytesIO(b"x" * 2048), filename="big.zip")
    with pytest.raises(UploadTooLarge):
        await save_upload(upload, tmp_path, "big.zip", 1024)
    assert list(tmp_path.iterdir()) == []


async def test_an_upload_is_written_whole(tmp_path) -> None:
    upload = UploadFile(io.BytesIO(b"x" * 3_000_000), filename="big.zip")
    path, size = await save_upload(upload, tmp_path, "big.zip", 4_000_000)
    assert size == 3_000_000 and path.stat().st_size == size
    assert [p.name for p in tmp_path.iterdir()] == [path.name]


def test_a_failed_save_leaves_nothing_behind(tmp_path, monkeypatch) -> None:
    def refuse(*_a):
        raise OSError("disk full")

    monkeypatch.setattr("src.helpers.media.os.replace", refuse)
    with pytest.raises(OSError):
        save_media_bytes(b"x", tmp_path, "shot.png")
    assert list(tmp_path.iterdir()) == []


def test_a_half_written_upload_is_not_listed(tmp_path) -> None:
    (tmp_path / ".abc_big.zip.part").write_bytes(b"x")
    (tmp_path / "abc_done.zip").write_bytes(b"x")
    assert list_media(tmp_path) == ["abc_done.zip"]


def test_names_keep_their_letters_and_lose_anything_dangerous() -> None:
    assert safe_filename("../../日本語 ゲーム.png").endswith("_日本語_ゲーム.png")
    assert "/" not in safe_filename("a/b\\c?.png")
    long = safe_filename("x" * 400 + ".png")
    assert len(long) < 300 and long.endswith(".png")


async def test_saving_art_that_fails_keeps_the_art_that_was_there(flow, monkeypatch) -> None:
    monkeypatch.setattr(save_game_asset, "DATA_ROOT", flow.tmp)
    monkeypatch.setattr(save_game_asset, "make_standard_previews", lambda *_a: None)
    await save_game_asset.save_game_asset(_png(), flow.game_id, "key_art")
    cover = flow.tmp / str(flow.user_id) / "games" / "Flow" / "key_art.png"
    before = cover.read_bytes()

    def refuse(*_a):
        raise OSError("disk full")

    monkeypatch.setattr(save_game_asset.os, "replace", refuse)
    with pytest.raises(OSError):
        await save_game_asset.save_game_asset(_png(), flow.game_id, "key_art")
    assert cover.read_bytes() == before
    assert [p.name for p in cover.parent.iterdir() if p.name.endswith(".part")] == []


async def test_a_database_failure_does_not_leave_the_upload_on_disk(tmp_path) -> None:
    from src.api.routes.games import _commit_or_remove

    saved = tmp_path / "shot.png"
    saved.write_bytes(b"x")

    class FailingDb:
        async def commit(self):
            raise RuntimeError("database down")

        async def rollback(self):
            pass

    with pytest.raises(RuntimeError):
        await _commit_or_remove(FailingDb(), [saved])
    assert not saved.exists()


async def test_a_version_cannot_come_back_while_its_save_is_in_the_trash(flow) -> None:
    made = await flow.client.post(
        f"{flow.game}/archives/save",
        data={"name": "Slot"},
        files={"file": ("a.sav", b"one", "application/octet-stream")},
    )
    archive = made.json()
    added = await flow.client.post(
        f"{flow.game}/archives/{archive['id']}/versions",
        files={"file": ("b.sav", b"two", "application/octet-stream")},
    )
    version = added.json()["versions"][0]["id"]
    await flow.client.delete(f"{flow.game}/archives/{archive['id']}/versions/{version}")
    await flow.client.delete(f"{flow.game}/archives/{archive['id']}")
    back = await flow.client.post(
        f"{flow.game}/archives/{archive['id']}/versions/{version}/restore"
    )
    assert back.status_code == 400


@pytest.fixture
def old(tmp_path, monkeypatch):
    """A person's data folder and the old shared one, both temporary."""
    root = tmp_path / "users"
    legacy = tmp_path / "games"
    legacy.mkdir()
    for module in (legacy_files, save_game_asset, game_info_file, repair):
        monkeypatch.setattr(module, "DATA_ROOT", root)
    monkeypatch.setattr(legacy_files, "LEGACY_ROOT", legacy)
    return SimpleNamespace(root=root, legacy=legacy)


def _write(path, data: bytes = b"data") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


async def _rename_game(flow, folder: str) -> None:
    async with SessionLocal() as db:
        (await db.get(Game, flow.game_id)).folder_location = folder
        await db.commit()


async def test_old_files_are_copied_into_the_numbered_folder_and_originals_stay(flow, old) -> None:
    await _rename_game(flow, "ELDEN-RING-2")
    shot = old.legacy / "ELDEN-RING" / "screenshots" / "ab_20260515191011_1.png"
    _write(shot, _png())
    _write(old.legacy / "ELDEN-RING" / "notes" / "sadas.md", b"note")
    _write(old.legacy / "ELDEN-RING" / "docs" / "ab_manual.pdf", b"doc")
    _write(old.legacy / "ELDEN-RING" / "world_map" / "tile.png", b"map")
    _write(old.legacy / "Nobody-Has-This" / "screenshots" / "x.png", b"x")

    async with SessionLocal() as db:
        found = await legacy_files.scan_old_files(db, flow.user_id)
        await db.commit()
    assert found["folders"][0]["files"] == {"screenshots": 1, "notes": 1, "docs": 1}
    assert found["no_game"] == ["Nobody-Has-This"]
    assert found["map_folders"] == 1

    async with SessionLocal() as db:
        done = await legacy_files.restore_old_files(db, flow.user_id)
    assert done == {"copied": 3, "failed": 0}
    home = old.root / str(flow.user_id) / "games" / "ELDEN-RING-2"
    assert (home / "screenshots" / shot.name).read_bytes() == _png()
    assert shot.is_file(), "the original stays"
    assert not (home / "world_map").exists()

    async with SessionLocal() as db:
        media = (await db.scalars(select(MediaItem).where(MediaItem.game_id == flow.game_id))).all()
        files = (
            await db.scalars(select(GameFileItem).where(GameFileItem.game_id == flow.game_id))
        ).all()
        assert [m.filename for m in media] == [shot.name]
        assert media[0].taken_source == "filename"
        assert [f.kind for f in files] == ["doc"]
        again = await legacy_files.restore_old_files(db, flow.user_id)
    assert again == {"copied": 0, "failed": 0}, "copying twice adds nothing"


async def test_a_different_file_with_the_same_name_is_never_overwritten(flow, old) -> None:
    await _rename_game(flow, "Game")
    _write(old.legacy / "Game" / "screenshots" / "a.png", b"old one")
    mine = old.root / str(flow.user_id) / "games" / "Game" / "screenshots" / "a.png"
    _write(mine, b"mine, different")
    async with SessionLocal() as db:
        done = await legacy_files.restore_old_files(db, flow.user_id)
    assert done == {"copied": 0, "failed": 1}
    assert mine.read_bytes() == b"mine, different"


async def test_a_listed_save_whose_file_is_only_in_the_old_folder_comes_back(flow, old) -> None:
    await _rename_game(flow, "minecraft")
    async with SessionLocal() as db:
        archive = GameArchive(id=uuid.uuid4(), game_id=flow.game_id, kind="world_save", name="W")
        db.add(archive)
        await db.flush()
        db.add(GameArchiveVersion(id=uuid.uuid4(), archive_id=archive.id, filename="w.zip", size=4))
        await db.commit()
        archive_id = archive.id
    _write(old.legacy / "minecraft" / "world_saves" / str(archive_id) / "w.zip")
    async with SessionLocal() as db:
        assert (await legacy_files.restore_old_files(db, flow.user_id))["copied"] == 1
    home = old.root / str(flow.user_id) / "games" / "minecraft"
    assert (home / "world_saves" / str(archive_id) / "w.zip").read_bytes() == b"data"


async def test_the_scan_reports_saves_and_documents_whose_file_is_gone(flow, old) -> None:
    async with SessionLocal() as db:
        archive = GameArchive(id=uuid.uuid4(), game_id=flow.game_id, kind="save", name="S")
        db.add(archive)
        await db.flush()
        db.add(GameArchiveVersion(id=uuid.uuid4(), archive_id=archive.id, filename="s.sav", size=4))
        db.add(GameFileItem(game_id=flow.game_id, kind="doc", filename="gone.pdf"))
        await db.commit()
    listed = await repair.games_with_problem(flow.user_id, "missing_media")
    assert [g["id"] for g in listed] == [str(flow.game_id)]
