"""Refresh workers keep requests responsive and report failures to their callers."""

import threading
from unittest.mock import AsyncMock, Mock

from src.database.models.anime import Anime, AnimeSeason
from src.features.metadata import refresh, refresh_job
from src.main import app  # noqa: F401 -- register the complete application model graph


async def test_metadata_healing_does_not_block_the_event_loop_or_overwrite_existing_fields(
    monkeypatch,
):
    main_thread = threading.get_ident()

    class Client:
        def get_by_id(self, identifier):
            assert identifier == 42
            assert threading.get_ident() != main_thread
            return {
                "id": 42,
                "id_mal": 19,
                "format": "TV",
                "poster_url": "provider-poster",
                "overview": "provider-description",
                "episode_count": 12,
                "score": 80,
            }

    show = Anime(
        title="Example",
        anilist_id="42",
        description="User description",
        seasons=[AnimeSeason(season_number=1)],
    )
    result = Mock()
    result.scalars.return_value.all.return_value = [show]
    db = AsyncMock()
    db.__aenter__.return_value = db
    db.execute.return_value = result
    monkeypatch.setattr(refresh, "SessionLocal", lambda: db)
    monkeypatch.setattr(refresh, "AniListClient", Client)

    assert await refresh.heal_all_anime_metadata() == 1
    assert show.description == "User description"
    assert show.poster_url == "provider-poster"
    assert show.external_id == "19"
    assert show.format == "TV"
    assert show.anilist_score == 80
    assert show.seasons[0].episode_count == 12
    db.commit.assert_awaited_once()


async def test_refresh_failure_finishes_progress_and_does_not_skip_other_finish_hooks(monkeypatch):
    db = AsyncMock()
    db.__aenter__.return_value = db
    db.execute.side_effect = RuntimeError("database unavailable")
    monkeypatch.setattr(refresh_job, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        refresh_job,
        "fill_missing_titles",
        AsyncMock(side_effect=RuntimeError("lookup unavailable")),
    )
    monkeypatch.setattr(refresh_job, "heal_all_anime_metadata", AsyncMock(return_value=3))
    monkeypatch.setattr(refresh_job, "_progress", refresh_job.Progress())
    results = []

    def failing_hook(_progress):
        raise RuntimeError("hook unavailable")

    monkeypatch.setattr(refresh_job, "finish_hooks", [failing_hook, results.append])
    result = await refresh_job.run("all")
    assert result["error"] == "database unavailable"
    assert result["running"] is False
    assert result["phase"] == "Done"
    assert result["finished_at"] is not None
    assert result["anime_metadata_healed"] == 3
    assert results == [result]

    await refresh_job.run("needed")
    assert results[-1]["mode"] == "needed"
    assert len(results) == 2
