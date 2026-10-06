"""Finding when a screenshot or clip was really taken."""

import io
from calendar import timegm
from datetime import datetime

from PIL import Image

from src.helpers.media_dates import detect_date, detect_from_stored, from_filename

NOW = timegm(datetime(2026, 10, 4, 12, 0, 0).timetuple())


def utc(*parts: int) -> int:
    return timegm(datetime(*parts).timetuple())


def test_capture_tool_file_names_give_the_date() -> None:
    assert from_filename("20260515191011_1.jpg", NOW) == utc(2026, 5, 15, 19, 10, 11)
    assert from_filename("Screenshot 2026-05-15 19-10-11.png", NOW) == utc(2026, 5, 15, 19, 10, 11)
    assert from_filename("ELDEN RING_2026.05.15_19.10.11.png", NOW) == utc(2026, 5, 15, 19, 10, 11)
    assert from_filename("boss 2026-05-15.png", NOW) == utc(2026, 5, 15)


def test_numbers_that_are_not_dates_are_ignored() -> None:
    assert from_filename("IMG_0001.png", NOW) is None
    assert from_filename("20261301000000.png", NOW) is None  # month 13
    assert from_filename("20990101000000.png", NOW) is None  # in the future
    assert from_filename("v1234567890123.png", NOW) is None


def _jpeg_with_exif(text: str) -> bytes:
    image = Image.new("RGB", (4, 4))
    exif = Image.Exif()
    exif[0x8769] = {36867: text}  # DateTimeOriginal
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif)
    return buffer.getvalue()


def test_photo_data_beats_the_file_name_and_modified_date() -> None:
    data = _jpeg_with_exif("2026:03:02 08:09:10")
    got = detect_date(data, "20260515191011.jpg", "screenshot", utc(2026, 9, 1), NOW)
    assert got == (utc(2026, 3, 2, 8, 9, 10), "photo")


def test_order_is_name_then_modified_then_upload() -> None:
    plain = io.BytesIO()
    Image.new("RGB", (2, 2)).save(plain, "PNG")
    data = plain.getvalue()
    assert detect_date(data, "20260515191011.png", "screenshot", utc(2026, 9, 1), NOW) == (
        utc(2026, 5, 15, 19, 10, 11),
        "filename",
    )
    assert detect_date(data, "shot.png", "screenshot", utc(2026, 9, 1), NOW) == (
        utc(2026, 9, 1),
        "file",
    )
    # the browser sends milliseconds
    assert detect_date(data, "shot.png", "screenshot", utc(2026, 9, 1) * 1000, NOW) == (
        utc(2026, 9, 1),
        "file",
    )
    # a modified date in the future is a wrong clock, not a date
    assert detect_date(data, "shot.png", "screenshot", NOW + 10**7, NOW) == (NOW, "uploaded")
    assert detect_date(data, "shot.png", "screenshot", None, NOW) == (NOW, "uploaded")


def test_redetect_reads_the_stored_file_not_its_modified_date(tmp_path) -> None:
    named = tmp_path / "ab12cd34_20260515191011_1.jpg"
    named.write_bytes(b"not an image")
    assert detect_from_stored(named, "screenshot") == (utc(2026, 5, 15, 19, 10, 11), "filename")

    nothing = tmp_path / "ab12cd34_shot.jpg"
    nothing.write_bytes(b"x")
    assert detect_from_stored(nothing, "screenshot") is None


async def test_title_and_date_can_be_set_and_cleared() -> None:
    import uuid
    from types import SimpleNamespace

    from sqlalchemy import delete

    from src.api.routes import games
    from src.api.schemas.game import GameCreate
    from src.database.models.media_item import MediaItem
    from src.database.models.user import User
    from src.database.session import SessionLocal
    from fastapi import Response

    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.commit()
        user_id = user.id
    try:
        owner = SimpleNamespace(id=user_id)
        async with SessionLocal() as db:
            real_create = games.create_game_folder
            games.create_game_folder = lambda *_a: None  # type: ignore[assignment]
            try:
                game = await games.create_game(
                    GameCreate(title="Dates", folder_location="Dates"), Response(), db, owner
                )
            finally:
                games.create_game_folder = real_create  # type: ignore[assignment]
            item = MediaItem(
                game_id=game.id,
                kind="screenshot",
                filename="a_b.png",
                taken_at=100,
                taken_source="file",
            )
            db.add(item)
            await db.commit()
            media_id = item.id

            out = await games.update_media_item(
                game.id,
                media_id,
                games.MediaItemUpdate(title="  Margit, first try  ", taken_at=utc(2026, 5, 15)),
                db,
                owner,
            )
            assert out["title"] == "Margit, first try"
            assert out["taken_at"] == utc(2026, 5, 15)
            assert out["taken_source"] == "manual"

            cleared = await games.update_media_item(
                game.id, media_id, games.MediaItemUpdate(title="", taken_at=None), db, owner
            )
            assert cleared["title"] is None
            assert cleared["taken_at"] is None and cleared["taken_source"] is None
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(User).where(User.id == user_id))
            await db.commit()


def _mp4_with_creation(unix: int, *, big: bool = False) -> bytes:
    import struct

    created = unix + 2082844800
    body = (
        bytes([1, 0, 0, 0]) + struct.pack(">QQ", created, created)
        if big
        else bytes([0, 0, 0, 0]) + struct.pack(">II", created, created)
    )
    mvhd = struct.pack(">I4s", 8 + len(body), b"mvhd") + body
    moov = struct.pack(">I4s", 8 + len(mvhd), b"moov") + mvhd
    ftyp = struct.pack(">I4s", 16, b"ftyp") + b"isom\x00\x00\x00\x00"
    return (
        ftyp + b"\x00\x00\x00\x10mdat" + b"\x00" * 8 + moov
    )  # moov after the media, as in many files


def test_video_creation_time_is_read_from_the_mp4_header() -> None:
    for big in (False, True):
        data = _mp4_with_creation(utc(2026, 5, 15, 19, 10, 11), big=big)
        assert detect_date(data, "render.mp4", "clip", None, NOW) == (
            utc(2026, 5, 15, 19, 10, 11),
            "video",
        )
    # a header with no usable time falls through to the next source
    assert detect_date(b"not a video", "clip 2026-05-15.mp4", "clip", None, NOW) == (
        utc(2026, 5, 15),
        "filename",
    )


def test_png_creation_time_chunk_is_used() -> None:
    from PIL.PngImagePlugin import PngInfo

    info = PngInfo()
    info.add_text("Creation Time", "Fri, 15 May 2026 19:10:11 +0000")
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, "PNG", pnginfo=info)
    assert detect_date(buffer.getvalue(), "shot.png", "screenshot", None, NOW) == (
        utc(2026, 5, 15, 19, 10, 11),
        "photo",
    )


async def test_detect_endpoint_reads_dates_from_stored_files(tmp_path, monkeypatch) -> None:
    """The route behind "Detect from file": changes only the files that say when
    they were taken, and leaves the rest (and any date set by hand) alone."""
    import uuid
    from types import SimpleNamespace

    from fastapi import Response
    from sqlalchemy import delete

    from src.api.routes import games
    from src.api.schemas.game import GameCreate
    from src.database.models.media_item import MediaItem
    from src.database.models.user import User
    from src.database.session import SessionLocal

    monkeypatch.setattr(games, "_DATA_ROOT", tmp_path)
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
    try:
        owner = SimpleNamespace(id=user_id)
        async with SessionLocal() as db:
            game = await games.create_game(
                GameCreate(title="Detect", folder_location="Detect"), Response(), db, owner
            )
            folder = tmp_path / str(user_id) / "games" / "Detect" / "screenshots"
            folder.mkdir(parents=True)
            (folder / "aaaaaaaa_20260515191011_1.jpg").write_bytes(b"x")
            (folder / "bbbbbbbb_shot.jpg").write_bytes(b"x")
            (folder / "cccccccc_2026-01-02.jpg").write_bytes(b"x")
            rows = {}
            for name in (
                "aaaaaaaa_20260515191011_1.jpg",
                "bbbbbbbb_shot.jpg",
                "cccccccc_2026-01-02.jpg",
            ):
                item = MediaItem(game_id=game.id, kind="screenshot", filename=name)
                db.add(item)
                rows[name] = item
            await db.commit()
            ids = [item.id for item in rows.values()]

            out = await games.detect_media_dates(
                game.id, games.DetectDatesRequest(ids=ids), db, owner
            )
            found = {m["filename"]: m for m in out["media"]}
            assert set(found) == {"aaaaaaaa_20260515191011_1.jpg", "cccccccc_2026-01-02.jpg"}
            assert found["aaaaaaaa_20260515191011_1.jpg"]["taken_at"] == utc(
                2026, 5, 15, 19, 10, 11
            )
            assert found["aaaaaaaa_20260515191011_1.jpg"]["taken_source"] == "filename"
            assert found["cccccccc_2026-01-02.jpg"]["taken_at"] == utc(2026, 1, 2)
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(User).where(User.id == user_id))
            await db.commit()
