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
