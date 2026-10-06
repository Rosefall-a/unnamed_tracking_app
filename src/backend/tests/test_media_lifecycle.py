"""Movies, TV shows and anime share one list / trash / restore / purge life
cycle (api/routes/media_common.py); this runs it through each real route."""

import pytest

from tests.test_game_files_flow import game_flow  # noqa: F401  (registers the "flow" fixture)

KINDS = [
    ("movie", {"title": "Heat", "status": "WATCHED", "rating_overall": 9}),
    ("tv", {"title": "Severance", "status": "IN_PROGRESS", "rating_overall": 8}),
    ("anime", {"title": "Noragami", "status": "WATCHED", "rating_overall": 9}),
]


@pytest.mark.parametrize(("kind", "payload"), KINDS)
async def test_list_trash_restore_and_purge(flow, kind: str, payload: dict) -> None:
    api = f"/api/{kind}"
    created = await flow.client.post(f"{api}/create", json=payload)
    assert created.status_code == 201, created.text
    row_id = created.json()["id"]

    listed = (await flow.client.get(f"{api}/list")).json()
    assert [r["title"] for r in listed["items"]] == [payload["title"]]
    assert listed["total"] == 1
    assert sum(listed["status_counts"].values()) == 1
    assert listed["score_ranks"] == {row_id: 1}
    assert (await flow.client.get(f"{api}/get/{row_id}")).json()["title"] == payload["title"]

    # a title that is not in the trash can be neither restored nor purged
    assert (await flow.client.post(f"{api}/{row_id}/restore")).status_code == 400
    assert (await flow.client.delete(f"{api}/{row_id}/purge")).status_code == 400

    assert (await flow.client.delete(f"{api}/delete/{row_id}")).status_code == 204
    assert (await flow.client.get(f"{api}/list")).json()["items"] == []
    trash = (await flow.client.get(f"{api}/trash")).json()
    assert [t["id"] for t in trash] == [row_id]
    assert trash[0]["title"] == payload["title"]

    restored = await flow.client.post(f"{api}/{row_id}/restore")
    assert restored.status_code == 200, restored.text
    assert restored.json()["id"] == row_id
    assert (await flow.client.get(f"{api}/trash")).json() == []

    await flow.client.delete(f"{api}/delete/{row_id}")
    assert (await flow.client.delete(f"{api}/{row_id}/purge")).status_code == 204
    assert (await flow.client.get(f"{api}/trash")).json() == []
    assert (await flow.client.get(f"{api}/get/{row_id}")).status_code == 404


@pytest.mark.parametrize(("kind", "payload"), KINDS)
async def test_search_and_favorite_filters(flow, kind: str, payload: dict) -> None:
    api = f"/api/{kind}"
    await flow.client.post(f"{api}/create", json=payload)
    other = {**payload, "title": "Zzz Unrelated", "favorite": True}
    await flow.client.post(f"{api}/create", json=other)

    found = (await flow.client.get(f"{api}/list", params={"search": "zzz"})).json()
    assert [r["title"] for r in found["items"]] == ["Zzz Unrelated"]
    favorites = (await flow.client.get(f"{api}/list", params={"favorite": "true"})).json()
    assert [r["title"] for r in favorites["items"]] == ["Zzz Unrelated"]
    # the tab counts follow the search, not the status filter
    assert sum(found["status_counts"].values()) == 1


@pytest.mark.parametrize(("kind", "payload"), KINDS)
async def test_search_treats_wildcards_as_plain_text(flow, kind: str, payload: dict) -> None:
    api = f"/api/{kind}"
    await flow.client.post(f"{api}/create", json=payload)
    await flow.client.post(f"{api}/create", json={**payload, "title": "100% Wolf_Man"})

    for text, expected in (
        ("%", ["100% Wolf_Man"]),
        ("_", ["100% Wolf_Man"]),
        ("100%", ["100% Wolf_Man"]),
    ):
        found = (await flow.client.get(f"{api}/list", params={"search": text})).json()
        assert [r["title"] for r in found["items"]] == expected, text


async def test_anime_search_and_tab_counts_use_every_title(flow) -> None:
    await flow.client.post(
        "/api/anime/create",
        json={"title": "Kimi no Na wa", "title_english": "Your Name", "status": "WATCHED"},
    )
    await flow.client.post("/api/anime/create", json={"title": "Other", "status": "WISHLIST"})

    found = (await flow.client.get("/api/anime/list", params={"search": "your name"})).json()
    assert [r["title"] for r in found["items"]] == ["Kimi no Na wa"]
    assert sum(found["status_counts"].values()) == 1
