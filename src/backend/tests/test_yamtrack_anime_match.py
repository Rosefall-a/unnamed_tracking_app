"""A Yamtrack anime row finds the show already in the library under another
spelling of its name instead of creating a second copy."""

import csv
import io

from src.database.models.anime import Anime
from src.database.session import SessionLocal
from src.features.imports.yamtrack import (
    YamtrackGroup,
    build_yamtrack_item,
    find_existing_anime,
)
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)

_CSV = b"""media_id,source,media_type,title,image,season_number,episode_number,score,status,notes,start_date,end_date,progress
50265,mal,anime,Supai Famirii,,,,9,Completed,,,2026-01-01,12
"""


async def _group_and_item() -> tuple[YamtrackGroup, Anime]:
    # built by hand: the importer skips anime rows for now, but the matching must
    # be right for when it is turned back on
    row = next(csv.DictReader(io.StringIO(_CSV.decode())))
    group = YamtrackGroup("mal", "50265", "anime", parent=row)
    item = build_yamtrack_item(group)
    assert isinstance(item, Anime)
    return group, item


async def test_matches_by_mal_id_even_when_the_titles_differ(flow) -> None:
    async with SessionLocal() as db:
        db.add(
            Anime(
                user_id=flow.user_id,
                title="Spy x Family",
                sort_title="spy x family",
                source="AniList",
                external_id="50265",
            )
        )
        await db.commit()
        group, item = await _group_and_item()
        found = await find_existing_anime(db, flow.user_id, group, item)
        assert found is not None and found.title == "Spy x Family"


async def test_matches_any_other_spelling_of_the_title(flow) -> None:
    async with SessionLocal() as db:
        db.add(
            Anime(
                user_id=flow.user_id,
                title="Spy x Family",
                sort_title="spy x family",
                title_romaji="Supai Famirii",
            )
        )
        await db.commit()
        group, item = await _group_and_item()
        found = await find_existing_anime(db, flow.user_id, group, item)
        assert found is not None and found.title_romaji == "Supai Famirii"


async def test_does_not_match_a_different_show(flow) -> None:
    async with SessionLocal() as db:
        db.add(Anime(user_id=flow.user_id, title="Other Show", sort_title="other show"))
        await db.commit()
        group, item = await _group_and_item()
        assert await find_existing_anime(db, flow.user_id, group, item) is None
