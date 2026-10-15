"""Changing a game's folder name moves its folder, so its art, notes and files
are still found."""

from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


async def test_a_new_folder_name_moves_the_folder_with_it(flow) -> None:
    old = flow.tmp / str(flow.user_id) / "games" / "Flow"
    old.mkdir(parents=True)
    (old / "key_art.png").write_bytes(b"cover")

    response = await flow.client.patch(f"/api/game/update/{flow.game_id}", json={"folder_location": "Flow-Renamed"})
    assert response.status_code == 200, response.text

    new = flow.tmp / str(flow.user_id) / "games" / "Flow-Renamed"
    assert (new / "key_art.png").read_bytes() == b"cover"
    assert not old.exists()


async def test_a_name_whose_folder_already_exists_on_disk_is_refused(flow) -> None:
    games = flow.tmp / str(flow.user_id) / "games"
    (games / "Flow").mkdir(parents=True)
    (games / "Taken").mkdir(parents=True)

    response = await flow.client.patch(f"/api/game/update/{flow.game_id}", json={"folder_location": "Taken"})
    assert response.status_code == 409
    assert (games / "Flow").is_dir()  # nothing moved
