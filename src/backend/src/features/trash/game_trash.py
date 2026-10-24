"""On-disk trash for whole games — the highest-blast-radius delete in the
app (cascades to screenshots, clips, notes, achievements, saves,
everything) previously had the weakest protection: instant and
permanent. This moves the entire game folder aside in one shot instead
of removing it, so features/trash/sweep.py has something to restore
from for 7 days."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID


def game_trash_dir(data_root: Path, game_id: UUID) -> Path:
    return data_root / "_trash" / str(game_id)


def _free_name(path: Path) -> Path:
    """`shot.png` -> `shot (restored).png`, then `(restored 2)`, ... until unused."""
    candidate = path.with_name(f"{path.stem} (restored){path.suffix}")
    n = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem} (restored {n}){path.suffix}")
        n += 1
    return candidate


def _move_without_overwriting(src: Path, dest: Path) -> None:
    """Move the folder `src` to `dest`. When `dest` already exists its files
    are kept: `src`'s files are merged in, and a file whose name is taken is
    moved under a new name instead of replacing the one already there."""
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        return
    for item in src.iterdir():
        target = dest / item.name
        if item.is_dir() and target.is_dir():
            _move_without_overwriting(item, target)
        elif target.exists():
            shutil.move(str(item), str(_free_name(target)))
        else:
            shutil.move(str(item), str(target))
    src.rmdir()


def move_game_to_trash(active_dir: Path, data_root: Path, game_id: UUID) -> None:
    if not active_dir.is_dir():
        return
    _move_without_overwriting(active_dir, game_trash_dir(data_root, game_id))


def restore_game_from_trash(active_dir: Path, data_root: Path, game_id: UUID) -> None:
    src = game_trash_dir(data_root, game_id)
    if not src.is_dir():
        return
    _move_without_overwriting(src, active_dir)


def purge_game_trash(data_root: Path, game_id: UUID) -> None:
    dest = game_trash_dir(data_root, game_id)
    if dest.is_dir():
        shutil.rmtree(dest, ignore_errors=True)
