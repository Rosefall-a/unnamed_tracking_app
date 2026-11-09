"""Automatic backups: a whole-database dump that a bad write never leaves
looking like a backup, rotation that never throws good backups away, and
account deletion that keeps files for an admin to remove."""

import subprocess
import uuid
from types import SimpleNamespace

import httpx
import pytest
from fastapi import Response
from sqlalchemy import delete, select

from src.api.routes import game_archives, games
from src.api.schemas.game import GameCreate
from src.core.auth import get_current_admin
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features.backup import scheduler, snapshot
from src.features.trash import sweep
from src.main import app

_LISTING = "".join(
    f"1; 2 3 TABLE DATA public {t} post_user\n"
    for t in ("users", "games", "movies", "tv_shows", "anime", "game_links")
)


@pytest.fixture
def fake_pg(monkeypatch):
    """pg_dump and pg_restore stand-ins: dumps write a small file, the
    listing names every library table unless a test changes it."""
    state = SimpleNamespace(listing=_LISTING, dump=b"PGDMP fake", stamp=1_800_000_000)

    def run(args, timeout):
        if args[0] == "pg_dump":
            target = args[-1].removeprefix("--file=")
            with open(target, "wb") as handle:
                handle.write(state.dump)
            return subprocess.CompletedProcess(args, 0, "", "")
        return subprocess.CompletedProcess(args, 0, state.listing, "")

    def clock():
        state.stamp += 1
        return state.stamp

    monkeypatch.setattr(snapshot, "_run", run)
    monkeypatch.setattr(snapshot.time, "time", clock)
    return state


def test_a_backup_is_written_checked_and_described(tmp_path, fake_pg) -> None:
    info = snapshot.write_backup(tmp_path, items=3)
    assert (tmp_path / info.name).read_bytes() == b"PGDMP fake"
    assert not list(tmp_path.glob("*.partial"))
    [listed] = snapshot.list_backups(tmp_path)
    assert listed.name == info.name and listed.items == 3 and listed.tables == 6
    assert listed.sha256 == info.sha256


def test_two_backups_in_the_same_second_both_survive(tmp_path, fake_pg, monkeypatch) -> None:
    monkeypatch.setattr(snapshot.time, "time", lambda: 1_800_000_000)
    a = snapshot.write_backup(tmp_path, items=1)
    b = snapshot.write_backup(tmp_path, items=1)
    assert a.name != b.name
    assert len(snapshot.list_backups(tmp_path)) == 2


def test_a_dump_missing_library_tables_is_thrown_away(tmp_path, fake_pg) -> None:
    fake_pg.listing = "1; 2 3 TABLE DATA public users post_user\n"
    with pytest.raises(snapshot.BackupError, match="games"):
        snapshot.write_backup(tmp_path, items=3)
    assert list(tmp_path.iterdir()) == []


def test_a_failed_dump_leaves_nothing_behind(tmp_path, monkeypatch) -> None:
    def run(args, timeout):
        if args[0] == "pg_dump":
            open(args[-1].removeprefix("--file="), "wb").write(b"half")
        raise snapshot.BackupError("pg_dump failed: connection lost")

    monkeypatch.setattr(snapshot, "_run", run)
    with pytest.raises(snapshot.BackupError):
        snapshot.write_backup(tmp_path, items=3)
    assert list(tmp_path.iterdir()) == []


def test_a_full_disk_is_refused_before_writing(tmp_path, fake_pg, monkeypatch) -> None:
    monkeypatch.setattr(
        snapshot.shutil, "disk_usage", lambda _p: SimpleNamespace(free=1024, total=0, used=0)
    )
    with pytest.raises(snapshot.BackupError):
        snapshot.write_backup(tmp_path, items=3)
    assert list(tmp_path.iterdir()) == []


def test_rotation_keeps_the_newest(tmp_path, fake_pg) -> None:
    names = [snapshot.write_backup(tmp_path, items=30).name for _ in range(5)]
    removed, held = snapshot.rotate(tmp_path, keep=3)
    assert (removed, held) == (2, None)
    assert [b.name for b in snapshot.list_backups(tmp_path)] == names[:1:-1]
    assert not list(tmp_path.glob(names[0].removesuffix(".dump") + "*"))


def test_zero_keeps_every_backup(tmp_path, fake_pg) -> None:
    for _ in range(4):
        snapshot.write_backup(tmp_path, items=30)
    assert snapshot.rotate(tmp_path, keep=0) == (0, None)
    assert len(snapshot.list_backups(tmp_path)) == 4


def test_a_library_that_suddenly_shrank_does_not_rotate_good_backups_away(
    tmp_path, fake_pg
) -> None:
    for _ in range(3):
        snapshot.write_backup(tmp_path, items=100)
    snapshot.write_backup(tmp_path, items=2)
    removed, held = snapshot.rotate(tmp_path, keep=2)
    assert removed == 0 and held
    assert len(snapshot.list_backups(tmp_path)) == 4


@pytest.mark.parametrize(
    "name", ["../database-1.dump", "database-1.meta.json", "x.dump", "database-1.dump/.."]
)
def test_only_backup_files_can_be_deleted(tmp_path, name) -> None:
    (tmp_path / "x.dump").write_text("{}")
    assert snapshot.delete_backup(tmp_path, name) is False
    assert (tmp_path / "x.dump").exists()


def _schedule(status: str | None, enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        enabled=enabled,
        interval_minutes=24 * 60,
        last_run_at=1_000 if status else None,
        last_result={"status": status} if status else None,
    )


def test_a_failed_run_is_due_again_after_an_hour() -> None:
    row = _schedule("failed")
    assert not scheduler.is_due(row, 1_000 + 59 * 60)
    assert scheduler.is_due(row, 1_000 + 60 * 60)


def test_a_good_run_waits_the_full_interval() -> None:
    row = _schedule("written")
    assert not scheduler.is_due(row, 1_000 + 23 * 60 * 60)
    assert scheduler.is_due(row, 1_000 + 24 * 60 * 60)


def test_the_first_run_is_due_straight_away() -> None:
    assert scheduler.is_due(_schedule(None), 1_000)


@pytest.mark.parametrize("status", [None, "written", "failed"])
def test_a_schedule_that_is_off_is_never_due(status) -> None:
    assert not scheduler.is_due(_schedule(status, enabled=False), 10**10)


def test_a_real_dump_of_this_database_passes_the_check(tmp_path) -> None:
    info = snapshot.write_backup(tmp_path, items=0)
    assert info.tables and info.tables >= 5
    restored = subprocess.run(
        ["pg_restore", "--schema-only", "--table=games", "--file=-", str(tmp_path / info.name)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "CREATE TABLE public.games" in restored.stdout


def test_the_sweep_looks_where_the_routes_put_files() -> None:
    user_id = uuid.uuid4()
    game = SimpleNamespace(user_id=user_id, folder_location="Celeste")
    assert sweep._DATA_ROOT == games._DATA_ROOT == game_archives._DATA_ROOT
    assert sweep._game_dir(game) == games._DATA_ROOT / str(user_id) / "games" / "Celeste"


@pytest.fixture
async def scratch(tmp_path, monkeypatch):
    users_root, user_root = tmp_path / "users", tmp_path / "user"
    monkeypatch.setattr(snapshot, "USER_FILE_ROOTS", (users_root, user_root))
    monkeypatch.setattr(snapshot, "DELETED_ACCOUNTS_ROOT", tmp_path / "deleted")
    monkeypatch.setattr(games, "create_game_folder", lambda *_a: None)
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="secret-hash",
            steam_api_key="secret-key",
        )
        db.add(user)
        await db.commit()
        user_id = user.id
        game = await games.create_game(
            GameCreate(title="Backup Flow", folder_location=f"Backup-{user_id.hex[:8]}"),
            Response(),
            db,
            SimpleNamespace(id=user_id),
        )
        assert game.id
    shot = users_root / str(user_id) / "games" / "Backup-x" / "screenshots" / "a.png"
    shot.parent.mkdir(parents=True)
    shot.write_bytes(b"png")
    (user_root / str(user_id) / "inbox").mkdir(parents=True)
    (user_root / str(user_id) / "inbox" / "b.png").write_bytes(b"png")
    yield SimpleNamespace(user_id=user_id, tmp=tmp_path)
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def test_deleting_an_account_sets_its_files_aside(scratch) -> None:
    admin = SimpleNamespace(id=uuid.uuid4())
    app.dependency_overrides[get_current_admin] = lambda: admin
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(f"/api/auth/users/{scratch.user_id}")
    finally:
        app.dependency_overrides.pop(get_current_admin, None)
    assert response.status_code == 200, response.text
    async with SessionLocal() as db:
        assert await db.scalar(select(User).where(User.id == scratch.user_id)) is None
    [kept] = list((scratch.tmp / "deleted").iterdir())
    assert (kept / "users" / "games" / "Backup-x" / "screenshots" / "a.png").is_file()
    assert (kept / "user" / "inbox" / "b.png").is_file()
    assert not (scratch.tmp / "users" / str(scratch.user_id)).exists()


async def test_leftovers_list_only_files_nothing_points_at(scratch, monkeypatch) -> None:
    from src.api.routes import backups

    users_root = scratch.tmp / "users"
    monkeypatch.setattr(backups, "_GAMES_DATA_ROOT", users_root)
    monkeypatch.setattr(backups, "DELETED_ACCOUNTS_ROOT", scratch.tmp / "deleted")
    monkeypatch.setattr(backups, "_OLD_BACKUPS_ROOT", scratch.tmp / "backups")
    stray_game = users_root / "_trash" / str(uuid.uuid4())
    stray_account = users_root / str(uuid.uuid4())
    old_backups = scratch.tmp / "backups" / str(scratch.user_id)
    # the whole-database backups live beside them and are never offered
    database_backups = scratch.tmp / "backups" / "database"
    for folder in (
        stray_game,
        stray_account,
        scratch.tmp / "deleted" / "old-account",
        old_backups,
        database_backups,
    ):
        folder.mkdir(parents=True)
        (folder / "f.bin").write_bytes(b"1234")

    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(id=uuid.uuid4())
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            listed = (await client.get("/api/settings/backups/leftovers")).json()
            kinds = sorted((item["kind"], item["bytes"]) for item in listed)
            assert kinds == [
                ("account_files", 4),
                ("deleted_account", 4),
                ("game_trash", 4),
                ("old_backups", 4),
            ]
            # the scratch user's own files still have an account, so they are not
            # offered; only that account's old backups are
            assert [item["kind"] for item in listed if str(scratch.user_id) in item["name"]] == [
                "old_backups"
            ]
            gone = await client.delete(
                f"/api/settings/backups/leftovers/game_trash/{stray_game.name}"
            )
            assert gone.status_code == 200
            refused = await client.delete(
                f"/api/settings/backups/leftovers/account_files/users-{scratch.user_id}"
            )
            assert refused.status_code == 404
            assert (
                await client.delete(
                    f"/api/settings/backups/leftovers/old_backups/{scratch.user_id}"
                )
            ).status_code == 200
            assert (
                await client.delete("/api/settings/backups/leftovers/old_backups/database")
            ).status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_admin, None)
    assert not old_backups.exists() and database_backups.exists()
    assert not stray_game.exists()
    assert stray_account.exists() and (users_root / str(scratch.user_id)).exists()
