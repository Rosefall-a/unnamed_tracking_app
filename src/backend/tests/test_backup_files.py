"""The optional files copy next to a database backup, and knowing which drive
backups are on. The database backup itself is covered in test_backups.py."""

import subprocess
import tarfile
from types import SimpleNamespace

import httpx
import pytest

from src.core.auth import get_current_admin
from src.features.backup import files_archive, scheduler, snapshot
from src.main import app

_LISTING = "".join(
    f"1; 2 3 TABLE DATA public {t} post_user\n"
    for t in ("users", "games", "movies", "tv_shows", "anime")
)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    """A backups folder, two file roots like /data/users and /data/user, and
    pg_dump and pg_restore stand-ins."""
    backups = tmp_path / "backups" / "database"
    users, user = tmp_path / "data" / "users", tmp_path / "data" / "user"
    files = {
        users / "u1" / "games" / "Hades" / "cover.jpg": b"cover",
        users / "u1" / "games" / "Hades" / "screenshots" / "a.png": b"shot",
        user / "u1" / "inbox" / "b.png": b"inbox",
        # left out: downloaded copies the app fetches again, and the trash
        users / "u1" / ".cache" / "page-files" / "x.webm": b"clip",
        users / "_trash" / "g1" / "old.png": b"old",
    }
    for path, body in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    stamp = SimpleNamespace(now=1_800_000_000)

    def run(args, timeout):
        if args[0] == "pg_dump":
            with open(args[-1].removeprefix("--file="), "wb") as handle:
                handle.write(b"PGDMP fake")
            return subprocess.CompletedProcess(args, 0, "", "")
        return subprocess.CompletedProcess(args, 0, _LISTING, "")

    def clock():
        stamp.now += 1
        return stamp.now

    monkeypatch.setattr(snapshot, "_run", run)
    monkeypatch.setattr(snapshot.time, "time", clock)
    monkeypatch.setattr(snapshot, "USER_FILE_ROOTS", (users, user))
    monkeypatch.setattr(snapshot, "DATABASE_DIR", backups)
    return SimpleNamespace(backups=backups, root=tmp_path, users=users, user=user)


def _backup_with_files(setup) -> snapshot.BackupInfo:
    info = snapshot.write_backup(setup.backups, items=30)
    info.files = files_archive.write_files(setup.backups, info.name)
    snapshot.write_info(setup.backups, info)
    return info


def test_the_files_copy_holds_every_file_and_puts_them_back(setup, tmp_path) -> None:
    info = _backup_with_files(setup)
    assert info.files["count"] == 3 and info.files["skipped"] == 0
    archive = snapshot.files_path(setup.backups, info.name)
    assert archive.name == info.name.removesuffix(".dump") + ".files.tar"
    assert not list(setup.backups.glob("*.partial"))

    restored = tmp_path / "restored"
    with tarfile.open(archive) as tar:
        tar.extractall(restored, filter="data")
    assert (restored / "users/u1/games/Hades/cover.jpg").read_bytes() == b"cover"
    assert (restored / "users/u1/games/Hades/screenshots/a.png").read_bytes() == b"shot"
    assert (restored / "user/u1/inbox/b.png").read_bytes() == b"inbox"
    assert not (restored / "users/u1/.cache").exists()
    assert not (restored / "users/_trash").exists()
    # the backup's own record says it has the copy
    [listed] = snapshot.list_backups(setup.backups)
    assert listed.files["size"] == archive.stat().st_size


def test_a_copy_that_cannot_fit_is_refused_and_leaves_nothing(setup, monkeypatch) -> None:
    info = snapshot.write_backup(setup.backups, items=30)
    monkeypatch.setattr(
        files_archive.shutil, "disk_usage", lambda _p: SimpleNamespace(free=10, total=0, used=0)
    )
    with pytest.raises(snapshot.BackupError, match="disk space"):
        files_archive.write_files(setup.backups, info.name)
    assert not list(setup.backups.glob("*.tar*"))


def test_deleting_or_rotating_a_backup_takes_its_files_copy_too(setup) -> None:
    names = [_backup_with_files(setup).name for _ in range(3)]
    assert snapshot.delete_backup(setup.backups, names[0])
    assert not snapshot.files_path(setup.backups, names[0]).exists()
    assert snapshot.rotate(setup.backups, keep=1) == (1, None)
    assert sorted(p.name for p in setup.backups.glob("*.tar")) == [
        names[2].removesuffix(".dump") + ".files.tar"
    ]


def test_only_the_newest_backups_keep_their_files_copy(setup) -> None:
    names = [_backup_with_files(setup).name for _ in range(4)]
    assert snapshot.prune_files(setup.backups, keep=2) == 2
    kept = {b.name: b.files for b in snapshot.list_backups(setup.backups)}
    # every database backup stays; only the two oldest lose the files copy
    assert set(kept) == set(names)
    assert [name for name in names if kept[name]] == names[2:]
    assert [snapshot.files_path(setup.backups, n).exists() for n in names] == [
        False,
        False,
        True,
        True,
    ]


class _FakeDB:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    async def commit(self):
        return None


@pytest.fixture
def schedule(setup, monkeypatch):
    """run_backup against a stand-in schedule row, so the real one is untouched."""
    row = SimpleNamespace(
        enabled=True, interval_minutes=1440, options={"keep": 7}, last_run_at=None, last_result={}
    )

    async def get_setting(_db):
        return row

    async def count_items():
        return 30

    monkeypatch.setattr(scheduler, "SessionLocal", _FakeDB)
    monkeypatch.setattr(scheduler, "get_setting", get_setting)
    monkeypatch.setattr(scheduler, "_count_items", count_items)
    return row


async def test_files_are_left_out_unless_turned_on(setup, schedule) -> None:
    result = await scheduler.run_backup()
    assert result["status"] == "written" and "files_size" not in result
    assert not list(setup.backups.glob("*.tar"))
    assert schedule.last_result["status"] == "written"


async def test_turned_on_each_backup_gets_its_files(setup, schedule) -> None:
    schedule.options = {"keep": 7, "include_files": True, "files_keep": 2}
    for _ in range(3):
        result = await scheduler.run_backup()
    assert result["status"] == "written" and result["files_size"] > 0
    assert len(snapshot.list_backups(setup.backups)) == 3
    assert len(list(setup.backups.glob("*.tar"))) == 2


async def test_a_failed_files_copy_keeps_the_database_backup(setup, schedule, monkeypatch) -> None:
    schedule.options = {"keep": 7, "include_files": True}

    def broken(*_args, **_kwargs):
        raise snapshot.BackupError("the disk went away")

    monkeypatch.setattr(files_archive, "write_files", broken)
    result = await scheduler.run_backup()
    assert result["status"] == "written"
    assert "disk went away" in result["files_error"]
    [kept] = snapshot.list_backups(setup.backups)
    assert kept.files is None


# a trimmed mount table as Docker Desktop shows it: data on C:, the backups
# folder mounted from another drive, and the container's own disk
_MOUNTS = """\
566 1 0:60 / / rw,relatime - overlay overlay rw
590 566 0:70 /Users/me/app/data /data rw,noatime - 9p C:\\134 rw,aname=drvfs;path=C:\\
591 590 0:71 /ArchiveBackups /data/backups rw,noatime - 9p D:\\134 rw,aname=drvfs;path=D:\\
"""


def test_backups_on_another_drive_are_told_apart(tmp_path) -> None:
    table = tmp_path / "mountinfo"
    table.write_text(_MOUNTS)
    backups = snapshot.drive_of(snapshot.Path("/data/backups/database"), table)
    data = snapshot.drive_of(snapshot.Path("/data/users"), table)
    assert backups == {"device": "D:\\", "label": "D:\\", "mounted": True}
    assert data is not None and data["label"] == "C:\\"
    assert backups["device"] != data["device"]


def test_the_same_drive_through_two_mounts_counts_as_one(tmp_path) -> None:
    table = tmp_path / "mountinfo"
    table.write_text(_MOUNTS.replace("0:71", "0:72").replace("D:\\134", "c:\\134"))
    backups = snapshot.drive_of(snapshot.Path("/data/backups"), table)
    data = snapshot.drive_of(snapshot.Path("/data/users"), table)
    assert backups is not None and data is not None
    assert backups["device"] == data["device"] == "C:\\"


def test_a_folder_only_inside_the_container_is_flagged(tmp_path) -> None:
    table = tmp_path / "mountinfo"
    table.write_text(_MOUNTS.splitlines()[0] + "\n")
    found = snapshot.drive_of(snapshot.Path("/data/backups"), table)
    assert found is not None and found["mounted"] is False
    assert snapshot.drive_of(snapshot.Path("/x"), tmp_path / "missing") is None


@pytest.mark.parametrize("files_keep", [0, scheduler.MAX_FILES_KEEP + 1])
async def test_files_keep_must_be_in_range(files_keep) -> None:
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(id=None)
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                "/api/settings/backups", json={"files_keep": files_keep}
            )
    finally:
        app.dependency_overrides.pop(get_current_admin, None)
    assert response.status_code == 400
