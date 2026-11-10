"""The optional copy of everyone's files that goes with a database backup.

The database backup holds every title, note and setting, but not the files:
covers, screenshots, clips, saves and uploads in /data/users and /data/user.
With this turned on (Settings > Administration > Backups, off by default
because it is far bigger), each backup also gets database-<time>.files.tar
beside its dump. Left out: the .cache folders, which hold downloaded copies
the app fetches again by itself, and the trash.

To put the files back, stop the app and, in the folder that holds data/,
extract it into data/:

    tar -xf database-<time>.files.tar -C data

Same care as the dump: written as .partial, flushed, read back in full and
counted before it gets its real name, so a half-written copy never looks
like a good one. A file that disappears while the copy is made (a cover
being replaced) is skipped and counted, never fatal.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tarfile
from collections.abc import Iterator
from pathlib import Path

from src.features.backup import snapshot

# folder names left out wherever they appear
SKIPPED_FOLDERS = frozenset({".cache", "_trash"})
_FREE_SPACE_MARGIN = 200 * 1024 * 1024


def _files(roots: tuple[Path, ...]) -> Iterator[tuple[Path, str]]:
    """Every file to copy, with the name it gets inside the archive
    ("users/<id>/...", "user/<id>/..."), so extracting into data/ puts it back."""
    for root in roots:
        if not root.is_dir():
            continue
        for folder, dirs, names in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in SKIPPED_FOLDERS)
            for name in sorted(names):
                path = Path(folder) / name
                # only plain files: a link would point outside the copy
                if path.is_symlink() or not path.is_file():
                    continue
                yield path, f"{root.name}/{path.relative_to(root).as_posix()}"


def measure(roots: tuple[Path, ...] | None = None) -> tuple[int, int]:
    """(file count, total bytes) a copy would hold right now."""
    count = total = 0
    for path, _name in _files(roots or snapshot.USER_FILE_ROOTS):
        try:
            total += path.stat().st_size
        except OSError:
            continue
        count += 1
    return count, total


def write_files(backup_dir: Path, backup_name: str, roots: tuple[Path, ...] | None = None) -> dict:
    """Writes and checks the files copy for one backup. Returns what goes in
    that backup's .meta.json under "files"."""
    roots = roots or snapshot.USER_FILE_ROOTS
    final = snapshot.files_path(backup_dir, backup_name)
    partial = final.with_name(final.name + ".partial")
    _count, expected = measure(roots)
    free = shutil.disk_usage(backup_dir).free
    if free < expected + _FREE_SPACE_MARGIN:
        raise snapshot.BackupError(
            f"Not enough disk space for the files copy: about {expected} bytes needed, {free} free."
        )
    added = skipped = 0
    try:
        with tarfile.open(partial, "w") as archive:
            for path, name in _files(roots):
                try:
                    archive.add(path, arcname=name, recursive=False)
                except OSError:
                    skipped += 1
                    continue
                added += 1
        with partial.open("rb") as handle:
            os.fsync(handle.fileno())
        # read it back: every file must be there and readable to the end
        digest = hashlib.sha256()
        with partial.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        with tarfile.open(partial, "r") as archive:
            found = sum(1 for member in archive if member.isfile())
        if found != added:
            raise snapshot.BackupError(f"The files copy holds {found} files, {added} were written.")
        size = partial.stat().st_size
        os.replace(partial, final)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    return {
        "name": final.name,
        "size": size,
        "count": added,
        "skipped": skipped,
        "sha256": digest.hexdigest(),
    }
