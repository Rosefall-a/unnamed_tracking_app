"""Moving a game folder in and out of the trash never deletes a file."""

import uuid

from src.features.trash.game_trash import (
    game_trash_dir,
    move_game_to_trash,
    restore_game_from_trash,
)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_restore_into_an_existing_folder_keeps_both_sets_of_files(tmp_path):
    game_id = uuid.uuid4()
    active = tmp_path / "user" / "games" / "Hades"
    _write(active / "screenshots" / "a.png", "old a")
    _write(active / "notes" / "run.md", "old note")
    move_game_to_trash(active, tmp_path, game_id)
    assert not active.exists()

    # something new lands at the same path while the game sits in the trash
    _write(active / "screenshots" / "a.png", "new a")
    _write(active / "screenshots" / "b.png", "new b")

    restore_game_from_trash(active, tmp_path, game_id)

    assert (active / "screenshots" / "a.png").read_text() == "new a"
    assert (active / "screenshots" / "a (restored).png").read_text() == "old a"
    assert (active / "screenshots" / "b.png").read_text() == "new b"
    assert (active / "notes" / "run.md").read_text() == "old note"
    assert not game_trash_dir(tmp_path, game_id).exists()


def test_trashing_twice_keeps_the_earlier_trashed_files(tmp_path):
    game_id = uuid.uuid4()
    active = tmp_path / "user" / "games" / "Hades"
    _write(active / "save.dat", "first")
    move_game_to_trash(active, tmp_path, game_id)
    _write(active / "save.dat", "second")
    move_game_to_trash(active, tmp_path, game_id)

    trash = game_trash_dir(tmp_path, game_id)
    assert sorted(p.read_text() for p in trash.iterdir()) == ["first", "second"]


def test_restore_without_a_trash_copy_leaves_the_folder_alone(tmp_path):
    active = tmp_path / "user" / "games" / "Hades"
    _write(active / "save.dat", "kept")
    restore_game_from_trash(active, tmp_path, uuid.uuid4())
    assert (active / "save.dat").read_text() == "kept"
