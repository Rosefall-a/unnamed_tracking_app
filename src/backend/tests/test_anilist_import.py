import datetime as dt
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.api.routes import anime as anime_routes
from src.database.models.anime import Anime, AnimeSeason
from src.features.imports import anilist as library_import
from src.features.metadata.anime import anilist_import
from src.features.metadata.anime.anilist_import import _map_entry


def test_anilist_entry_maps_status_progress_and_metadata():
    result = _map_entry(
        {
            "status": "COMPLETED",
            "score": 8,
            "progress": 12,
            "repeat": 1,
            "priority": 2,
            "notes": "great",
            "startedAt": {"year": 2025, "month": 2, "day": 3},
            "completedAt": {"year": 2025, "month": 4, "day": 5},
            "media": {
                "id": 123,
                "title": {"english": "Example Anime", "romaji": "Example Anime"},
                "description": "desc",
                "startDate": {"year": 2024, "month": 1, "day": 2},
                "episodes": 12,
                "duration": 24,
                "format": "TV",
                "genres": ["Action"],
                "countryOfOrigin": "JP",
                "studios": {"nodes": [{"name": "Studio"}]},
                "coverImage": {"extraLarge": "poster", "large": "poster-small"},
                "bannerImage": "backdrop",
                "averageScore": 85,
                "siteUrl": "https://anilist.co/anime/123",
            },
        }
    )

    assert result is not None
    assert result["anilist_id"] == "123"
    assert result["status"] == "WATCHED"
    assert result["progress"] == 12
    assert result["rating_overall"] == 8
    assert result["anilist_score"] == 8.5
    assert result["start_date"] == "2025-02-03"
    assert result["end_date"] == "2025-04-05"
    assert result["episode_count"] == 12


def test_anilist_entry_ignores_missing_media_id():
    assert _map_entry({"status": "PLANNING", "media": {}}) is None


@pytest.mark.parametrize("through_route", [False, True])
@pytest.mark.asyncio
async def test_existing_anilist_import_updates_dates_and_repeat_count(monkeypatch, through_route):
    entry = _map_entry(
        {
            "status": "COMPLETED",
            "repeat": 2,
            "progress": 12,
            "startedAt": {"year": 2025, "month": 1, "day": 2},
            "completedAt": {"year": 2025, "month": 2, "day": 3},
            "media": {
                "id": 123,
                "title": {"english": "Example"},
                "startDate": {"year": 2024, "month": 3, "day": 4},
                "episodes": 12,
            },
        }
    )
    client = SimpleNamespace(fetch_user_anime=lambda _username: [entry])
    monkeypatch.setattr(anilist_import, "AniListImportClient", lambda: client)
    monkeypatch.setattr(library_import, "AniListImportClient", lambda: client)
    show = Anime(id=uuid4(), title="Old", seasons=[AnimeSeason(season_number=1)])
    session = AsyncMock()
    session.scalar.return_value = show
    if through_route:
        result = await anime_routes.import_anilist_library(
            anime_routes.AniListImportRequest(username="example", update_existing=True),
            session,
            SimpleNamespace(id=uuid4()),
        )
        result = result.model_dump()
    else:
        result = await library_import.import_anilist_library(session, uuid4(), "example", True)
    assert result == {"fetched": 1, "created": 0, "updated": 1, "skipped": 0, "errors": []}
    assert show.first_air_date == dt.date(2024, 3, 4)
    assert show.start_date == dt.date(2025, 1, 2)
    assert show.end_date == dt.date(2025, 2, 3)
    assert show.rewatches == 2
    assert show.seasons[0].episodes_watched == 12
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_anilist_commit_is_reported_without_counting_an_update(monkeypatch):
    entry = _map_entry({"media": {"id": 1, "title": {"english": "Example"}}})
    monkeypatch.setattr(
        library_import,
        "AniListImportClient",
        lambda: SimpleNamespace(fetch_user_anime=lambda _username: [entry]),
    )
    session = AsyncMock()
    session.scalar.return_value = Anime(
        id=uuid4(), title="Old", seasons=[AnimeSeason(season_number=1)]
    )
    session.commit.side_effect = SQLAlchemyError("commit failed")
    result = await library_import.import_anilist_library(session, uuid4(), "example", True)
    assert result["created"] == result["updated"] == 0
    assert result["skipped"] == 1
    assert result["errors"] == ["Example: commit failed"]
    session.rollback.assert_awaited_once()
