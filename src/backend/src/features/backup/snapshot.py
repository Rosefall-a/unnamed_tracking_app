"""Writes, checks and rotates whole-database backups.

A backup is one pg_dump file (custom format) per run in
/data/backups/database/, with a small .meta.json next to it holding its
checksum and how many library items the database had. It covers every
table, so restoring it brings back the whole server as it was:

    docker exec -i <db container> pg_restore --clean --if-exists \\
        -U <user> -d <database> < data/backups/database/database-<time>.dump

Files (covers, screenshots, saves) are not inside it; they stay in
/data/users and /data/user. An admin can turn on a copy of them next to each
backup (files_archive.py), off by default because it is far bigger.

/data/backups can be its own folder or drive: BACKUP_FOLDER in .env is
mounted there by the compose files, and drive_of() says where it really is.

Safety rules, in the order they apply:
1. The dump is written as .partial, flushed to disk, then opened with
   pg_restore --list before it gets its real name, so a crash, a full disk or
   a broken dump never leaves a file that looks like a good backup.
2. Old backups are removed only after a newer one has passed that check.
3. When the newest backup holds far fewer items than the one before it,
   nothing is removed: a library emptied by mistake must not rotate the good
   backups away.
4. Backups are only ever deleted by rotation or by an admin, one at a time.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy.engine import make_url

from src.core.config import settings

BACKUP_ROOT = Path("/data/backups")
DATABASE_DIR = BACKUP_ROOT / "database"
# where each person's files live, see games.py and media.py
USER_FILE_ROOTS = (Path("/data/users"), Path("/data/user"))
# a deleted account's files wait here until an admin removes them
DELETED_ACCOUNTS_ROOT = Path("/data/deleted_accounts")

BACKUP_NAME = re.compile(r"^database-\d+\.dump$")
FILES_SUFFIX = ".files.tar"
# tables a dump must hold data for to count as a backup at all
_REQUIRED_TABLES = ("users", "games", "movies", "tv_shows", "anime")
# a newest backup under half the previous one's items holds rotation back
_SHRINK_RATIO = 0.5
_SHRINK_MIN_ITEMS = 20
# free space a backup leaves on the disk, on top of its expected size
_FREE_SPACE_MARGIN = 200 * 1024 * 1024
_DUMP_TIMEOUT_SECONDS = 60 * 60


class BackupError(Exception):
    pass


@dataclass
class BackupInfo:
    name: str
    created_at: int
    size: int
    sha256: str | None
    items: int | None
    tables: int | None
    # the copy of everyone's files made with it, see files_archive.py:
    # {"name", "size", "count", "skipped"}, or None when it has none
    files: dict | None = None


def _pg_env() -> dict[str, str]:
    url = make_url(settings.DATABASE_URL)
    env = dict(os.environ)
    env.update(
        {
            "PGHOST": url.host or "localhost",
            "PGPORT": str(url.port or 5432),
            "PGUSER": url.username or "",
            "PGPASSWORD": url.password or "",
            "PGDATABASE": url.database or "",
        }
    )
    return env


def _run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            args, env=_pg_env(), capture_output=True, text=True, timeout=timeout, check=False
        )
    except FileNotFoundError as exc:
        raise BackupError(f"{args[0]} is not installed in the backend container.") from exc
    except subprocess.TimeoutExpired as exc:
        raise BackupError(f"{args[0]} took longer than {timeout} seconds.") from exc
    if result.returncode != 0:
        raise BackupError(f"{args[0]} failed: {result.stderr.strip()[:500]}")
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_dir(path: Path) -> None:
    # makes the rename itself survive a power cut; not possible on Windows
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _meta_path(backup: Path) -> Path:
    return backup.with_name(backup.name.rsplit(".", 1)[0] + ".meta.json")


def check_dump(path: Path) -> int:
    """Opens a dump with pg_restore and returns how many tables it holds data
    for. Raises when it cannot be read or is missing a library table."""
    listing = _run(["pg_restore", "--list", str(path)], timeout=10 * 60).stdout
    tables = set(re.findall(r"TABLE DATA \S+ (\S+) ", listing))
    missing = [name for name in _REQUIRED_TABLES if name not in tables]
    if missing:
        raise BackupError(f"The dump has no data for: {', '.join(missing)}.")
    return len(tables)


def _expected_size(backup_dir: Path) -> int:
    previous = list_backups(backup_dir)
    return previous[0].size * 2 if previous else 50 * 1024 * 1024


def write_backup(backup_dir: Path, items: int) -> BackupInfo:
    """Dumps and checks one backup, see rules 1 and 2 in the module notes.
    `items` is how many library entries the database holds right now."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    needed = _expected_size(backup_dir) + _FREE_SPACE_MARGIN
    free = shutil.disk_usage(backup_dir).free
    if free < needed:
        raise BackupError(f"Not enough disk space: about {needed} bytes needed, {free} free.")

    stamp = int(time.time())
    while (backup_dir / f"database-{stamp}.dump").exists():
        stamp += 1
    final = backup_dir / f"database-{stamp}.dump"
    partial = final.with_name(final.name + ".partial")
    try:
        _run(
            ["pg_dump", "--format=custom", "--no-owner", f"--file={partial}"],
            timeout=_DUMP_TIMEOUT_SECONDS,
        )
        _fsync_file(partial)
        tables = check_dump(partial)
        digest = _sha256(partial)
        size = partial.stat().st_size
        os.replace(partial, final)
        _fsync_dir(backup_dir)
    except Exception:
        partial.unlink(missing_ok=True)
        raise

    info = BackupInfo(
        name=final.name, created_at=stamp, size=size, sha256=digest, items=items, tables=tables
    )
    write_info(backup_dir, info)
    return info


def write_info(backup_dir: Path, info: BackupInfo) -> None:
    meta = _meta_path(backup_dir / info.name)
    tmp = meta.with_name(meta.name + ".partial")
    tmp.write_text(json.dumps(asdict(info)))
    os.replace(tmp, meta)


def files_path(backup_dir: Path, name: str) -> Path:
    """Where the copy of everyone's files for one backup goes, if it has one."""
    return backup_dir / (name.rsplit(".", 1)[0] + FILES_SUFFIX)


def read_info(backup: Path) -> BackupInfo:
    try:
        return BackupInfo(**json.loads(_meta_path(backup).read_text()))
    except (OSError, ValueError, TypeError):
        stat = backup.stat()
        return BackupInfo(
            name=backup.name,
            created_at=int(backup.name.split("-")[1].split(".")[0]),
            size=stat.st_size,
            sha256=None,
            items=None,
            tables=None,
        )


def list_backups(backup_dir: Path) -> list[BackupInfo]:
    """Newest first."""
    if not backup_dir.is_dir():
        return []
    found = [read_info(p) for p in backup_dir.iterdir() if BACKUP_NAME.match(p.name)]
    return sorted(found, key=lambda b: b.created_at, reverse=True)


def delete_backup(backup_dir: Path, name: str) -> bool:
    if not BACKUP_NAME.match(name):
        return False
    path = backup_dir / name
    if not path.is_file():
        return False
    path.unlink()
    files_path(backup_dir, name).unlink(missing_ok=True)
    _meta_path(path).unlink(missing_ok=True)
    return True


def prune_files(backup_dir: Path, keep: int) -> int:
    """Removes the files copy from every backup past the newest `keep` that
    have one. The database backup itself stays. Returns how many went."""
    removed = 0
    with_files = [b for b in list_backups(backup_dir) if b.files]
    for backup in with_files[keep:]:
        files_path(backup_dir, backup.name).unlink(missing_ok=True)
        backup.files = None
        write_info(backup_dir, backup)
        removed += 1
    return removed


def rotate(backup_dir: Path, keep: int) -> tuple[int, str | None]:
    """Removes the oldest backups past `keep` (0 keeps every one). Returns how
    many were removed, and why nothing was when rotation was held back."""
    if keep <= 0:
        return 0, None
    backups = list_backups(backup_dir)
    if len(backups) <= keep:
        return 0, None
    newest, previous = backups[0], backups[1]
    if (
        newest.items is not None
        and previous.items is not None
        and previous.items >= _SHRINK_MIN_ITEMS
        and newest.items < previous.items * _SHRINK_RATIO
    ):
        return 0, (
            f"the newest backup has {newest.items} items, the one before had "
            f"{previous.items}, so no old backups were removed"
        )
    removed = 0
    for stale in backups[keep:]:
        if delete_backup(backup_dir, stale.name):
            removed += 1
    return removed, None


MOUNT_TABLE = Path("/proc/self/mountinfo")


def _unescape(text: str) -> str:
    # the mount table writes a space as \040 and a backslash as \134
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), text)


def drive_of(path: Path, table: Path = MOUNT_TABLE) -> dict | None:
    """Which disk a folder really lives on, read from the container's mount
    table: {"device", "label", "mounted"}. The label is what a person
    recognises, such as C:\\ or D:\\ under Docker Desktop, or /dev/sdb1 on
    Linux. "mounted" is False when the folder is only inside the container,
    where it is lost when the container is removed. None when unknown."""
    try:
        lines = table.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    target = str(path)
    found: dict | None = None
    found_length = -1
    for line in lines:
        left, _sep, right = line.partition(" - ")
        fields, tail = left.split(), right.split()
        if len(fields) < 5 or len(tail) < 2:
            continue
        mount_point = _unescape(fields[4])
        inside = target == mount_point or target.startswith(mount_point.rstrip("/") + "/")
        # the deepest mount holding the folder is the one it is really on
        if not inside or len(mount_point) <= found_length:
            continue
        fstype, source = tail[0], _unescape(tail[1])
        # a Windows drive shared by Docker Desktop is named by its letter,
        # whichever mount it comes through; anything else by its device number
        windows_drive = re.match(r"^[A-Za-z]:\\", source)
        found_length = len(mount_point)
        found = {
            "device": source[:3].upper() if windows_drive else f"{fields[2]} {source}",
            "label": source,
            "mounted": mount_point != "/" and fstype != "overlay",
        }
    return found


def storage_report(backup_dir: Path = BACKUP_ROOT) -> dict:
    """Where backups and the files they protect each live, for Settings."""
    backups, data = drive_of(backup_dir), drive_of(USER_FILE_ROOTS[0])
    same = None
    if backups is not None and data is not None:
        same = backups.get("device") == data.get("device")
    return {"backups": backups, "data": data, "same_drive": same}


def clear_partials(backup_dir: Path, older_than_seconds: int = 24 * 60 * 60) -> None:
    """Leftovers from a run that died mid-write."""
    if not backup_dir.is_dir():
        return
    cutoff = time.time() - older_than_seconds
    for path in backup_dir.glob("*.partial"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            pass
