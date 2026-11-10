"""The calendar's Log button does what it says, games keep their real dates, and
the calendar calls game activity what it is."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from src.database.models.achievement import Achievement
from src.database.models.game import Game, GameStatus
from src.database.models.game_field_change import GameFieldChange
from src.database.session import SessionLocal
from src.features.game_finish_dates import correct_finish_dates
from src.helpers import game_info_file, save_game_asset
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)

DAY = "2022-06-27"
DAY_NOON = int(datetime(2022, 6, 27, 12, tzinfo=UTC).timestamp())


def _log(media_type: str, media_id, action: str, day: str = DAY, **extra) -> dict:
    return {
        "media_type": media_type,
        "media_id": str(media_id),
        "action": action,
        "event_date": day,
        **extra,
    }


async def _game(flow) -> Game:
    async with SessionLocal() as db:
        return await db.get(Game, flow.game_id)


async def test_beating_and_mastering_a_game_set_status_and_date(
    flow, tmp_path, monkeypatch
) -> None:
    for module in (save_game_asset, game_info_file):
        monkeypatch.setattr(module, "DATA_ROOT", tmp_path)
    beat = await flow.client.post("/api/activity/log", json=_log("game", flow.game_id, "finished"))
    assert beat.status_code == 201, beat.text
    assert beat.json()["event_type"] == "finished"
    game = await _game(flow)
    assert game.status == GameStatus.BEATEN
    assert game.completion_date == DAY_NOON

    await flow.client.post("/api/activity/log", json=_log("game", flow.game_id, "mastered"))
    assert (await _game(flow)).status == GameStatus.MASTERED
    # beating it again does not take away Mastered
    await flow.client.post("/api/activity/log", json=_log("game", flow.game_id, "finished"))
    assert (await _game(flow)).status == GameStatus.MASTERED


async def test_playing_a_game_moves_it_on_and_never_moves_last_played_back(
    flow, tmp_path, monkeypatch
) -> None:
    for module in (save_game_asset, game_info_file):
        monkeypatch.setattr(module, "DATA_ROOT", tmp_path)
    await flow.client.post("/api/activity/log", json=_log("game", flow.game_id, "played"))
    game = await _game(flow)
    assert game.status == GameStatus.PLAYED
    assert game.last_played_at == DAY_NOON
    await flow.client.post(
        "/api/activity/log", json=_log("game", flow.game_id, "played", "2020-01-01")
    )
    assert (await _game(flow)).last_played_at == DAY_NOON

    entries = (await flow.client.get("/api/calendar/games")).json()
    played = [e for e in entries if e["kind"] == "game_played"]
    assert [e["date"] for e in played] == [DAY]


async def test_buying_a_wishlisted_game_moves_it_to_backlog(flow, tmp_path, monkeypatch) -> None:
    for module in (save_game_asset, game_info_file):
        monkeypatch.setattr(module, "DATA_ROOT", tmp_path)
    async with SessionLocal() as db:
        (await db.get(Game, flow.game_id)).status = GameStatus.WISHLIST
        await db.commit()
    await flow.client.post("/api/activity/log", json=_log("game", flow.game_id, "bought"))
    game = await _game(flow)
    assert game.status == GameStatus.BACKLOG
    assert game.purchase_date == DAY_NOON


async def test_finishing_a_show_ticks_off_its_episodes_and_reports_unknown_seasons(flow) -> None:
    show = (
        await flow.client.post(
            "/api/tv/create",
            json={
                "title": "Severance",
                "status": "IN_PROGRESS",
                "seasons": [
                    {"season_number": 1, "episode_count": 9},
                    {"season_number": 2},
                ],
            },
        )
    ).json()
    done = await flow.client.post("/api/activity/log", json=_log("tv", show["id"], "finished"))
    assert done.status_code == 201, done.text
    assert done.json()["detail"] == "1 season with no episode count"

    after = (await flow.client.get(f"/api/tv/get/{show['id']}")).json()
    assert after["status"] == "WATCHED"
    season = next(s for s in after["seasons"] if s["season_number"] == 1)
    assert season["episodes_watched"] == 9

    history = (await flow.client.get("/api/activity", params={"days": 36500})).json()
    episodes = next(e for e in history if e["event_type"] == "episodes_watched")
    assert (episodes["count"], episodes["event_date"]) == (9, DAY)


async def test_watching_a_movie_marks_it_watched(flow) -> None:
    movie = (await flow.client.post("/api/movie/create", json={"title": "Heat"})).json()
    logged = await flow.client.post(
        "/api/activity/log", json=_log("movie", movie["id"], "finished")
    )
    assert logged.status_code == 201, logged.text
    assert (await flow.client.get(f"/api/movie/get/{movie['id']}")).json()["status"] == "WATCHED"


async def test_logging_episodes_only_adds_to_history(flow) -> None:
    show = (await flow.client.post("/api/anime/create", json={"title": "Noragami"})).json()
    await flow.client.post("/api/activity/log", json=_log("anime", show["id"], "episodes", count=3))
    await flow.client.post("/api/activity/log", json=_log("anime", show["id"], "episodes", count=2))
    history = (await flow.client.get("/api/activity", params={"days": 36500})).json()
    assert [(e["event_type"], e["count"]) for e in history] == [("episodes_watched", 5)]


async def test_wrong_actions_future_dates_and_other_peoples_titles_are_refused(flow) -> None:
    movie = (await flow.client.post("/api/movie/create", json={"title": "Heat"})).json()
    wrong = await flow.client.post("/api/activity/log", json=_log("movie", movie["id"], "played"))
    assert wrong.status_code == 400
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    future = await flow.client.post(
        "/api/activity/log", json=_log("movie", movie["id"], "finished", tomorrow)
    )
    assert future.status_code == 400
    missing = await flow.client.post(
        "/api/activity/log",
        json=_log("game", "00000000-0000-0000-0000-000000000000", "played"),
    )
    assert missing.status_code == 404


async def _mastered(
    flow,
    completion: int,
    unlocked: tuple[bool, ...] = (True, True),
    seen: int = DAY_NOON + 3600,
) -> None:
    """A game a sync marked Mastered. `seen` is when the sync first saved the
    achievements, which a real sync always does before it stamps the date."""
    async with SessionLocal() as db:
        game = await db.get(Game, flow.game_id)
        game.status = GameStatus.MASTERED
        game.completion_date = completion
        for index, is_unlocked in enumerate(unlocked):
            db.add(
                Achievement(
                    game_id=flow.game_id,
                    external_id=str(index),
                    name=f"A{index}",
                    unlocked=is_unlocked,
                    unlocked_at=DAY_NOON - index if is_unlocked else None,
                    provider="Steam",
                    created_at=seen,
                )
            )
        await db.commit()


async def _added_later(flow, when: int, unlocked_at: int | None = None) -> None:
    """An achievement the game gained after it was mastered (an update or DLC)."""
    async with SessionLocal() as db:
        db.add(
            Achievement(
                game_id=flow.game_id,
                external_id=f"dlc-{when}",
                name="DLC",
                unlocked=unlocked_at is not None,
                unlocked_at=unlocked_at,
                provider="Steam",
                created_at=when,
            )
        )
        await db.commit()


async def _correct(flow) -> int:
    async with SessionLocal() as db:
        changed = await correct_finish_dates(db, flow.user_id)
        await db.commit()
    return changed


async def test_a_game_mastered_by_an_import_gets_the_day_of_its_last_unlock(flow) -> None:
    await _mastered(flow, completion=DAY_NOON + 400 * 86400)
    assert await _correct(flow) == 1
    assert (await _game(flow)).completion_date == DAY_NOON
    assert await _correct(flow) == 0


async def test_an_earlier_date_is_kept(flow) -> None:
    await _mastered(flow, completion=DAY_NOON - 86400)
    assert await _correct(flow) == 0


async def test_a_game_with_achievements_left_keeps_its_date(flow) -> None:
    later = DAY_NOON + 86400
    await _mastered(flow, completion=later, unlocked=(True, False))
    assert await _correct(flow) == 0
    assert (await _game(flow)).completion_date == later


async def test_a_date_someone_typed_in_is_kept(flow) -> None:
    later = DAY_NOON + 86400
    await _mastered(flow, completion=later)
    async with SessionLocal() as db:
        db.add(
            GameFieldChange(
                game_id=flow.game_id,
                field_name="completion_date",
                old_value=None,
                new_value=str(later),
                changed_at=later,
            )
        )
        await db.commit()
    assert await _correct(flow) == 0
    assert (await _game(flow)).completion_date == later


def _migration_sql() -> tuple[str, ...]:
    import importlib.util
    from pathlib import Path

    path = next(Path("src/database/migrations/versions").glob("d8f2b6a4e1c3_*.py"))
    spec = importlib.util.spec_from_file_location("true_finish_dates", path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module.FIX_FINISH_DATES


async def _run_migration() -> None:
    from sqlalchemy import text

    async with SessionLocal() as db:
        for statement in _migration_sql():
            await db.execute(text(statement))
        await db.commit()


async def test_the_update_fixes_dates_already_saved_on_the_import_day(flow) -> None:
    await _mastered(flow, completion=DAY_NOON + 400 * 86400)
    await _run_migration()
    assert (await _game(flow)).completion_date == DAY_NOON


async def test_the_update_keeps_typed_dates_and_unfinished_games(flow) -> None:
    later = DAY_NOON + 86400
    await _mastered(flow, completion=later, unlocked=(True, False))
    await _run_migration()
    assert (await _game(flow)).completion_date == later


async def test_achievements_added_after_mastering_do_not_block_the_real_date(flow) -> None:
    stamped = DAY_NOON + 400 * 86400
    await _mastered(flow, completion=stamped)
    await _added_later(flow, when=stamped + 86400)
    assert await _correct(flow) == 1
    assert (await _game(flow)).completion_date == DAY_NOON


async def test_unlocking_achievements_added_later_keeps_the_first_finish(flow) -> None:
    await _mastered(flow, completion=DAY_NOON + 3600)
    await _added_later(flow, when=DAY_NOON + 86400, unlocked_at=DAY_NOON + 2 * 86400)
    assert await _correct(flow) == 1
    assert (await _game(flow)).completion_date == DAY_NOON
    assert await _correct(flow) == 0


async def test_the_update_ignores_achievements_added_after_mastering(flow) -> None:
    stamped = DAY_NOON + 400 * 86400
    await _mastered(flow, completion=stamped)
    await _added_later(flow, when=stamped + 86400)
    await _run_migration()
    assert (await _game(flow)).completion_date == DAY_NOON


async def test_a_game_set_to_mastered_by_hand_before_its_achievements_synced_is_kept(
    flow,
) -> None:
    by_hand = DAY_NOON + 86400
    await _mastered(flow, completion=by_hand, unlocked=(True, False), seen=by_hand + 60)
    assert await _correct(flow) == 0
    await _run_migration()
    assert (await _game(flow)).completion_date == by_hand


async def _sync(flow, rows: list[dict]) -> None:
    from src.api.routes.library_sync import _replace_achievements

    async with SessionLocal() as db:
        await _replace_achievements(db, flow.game_id, "Steam", rows)
        await db.commit()


async def _stored(flow) -> dict[str, int | None]:
    async with SessionLocal() as db:
        return {
            a.external_id: a.unlocked_at
            for a in (
                await db.execute(select(Achievement).where(Achievement.game_id == flow.game_id))
            ).scalars()
        }


def _row(external_id: str, unlocked_at: int | None = None) -> dict:
    return {
        "external_id": external_id,
        "name": external_id,
        "unlocked": unlocked_at is not None,
        "unlocked_at": unlocked_at,
    }


async def test_an_empty_answer_from_a_provider_keeps_every_achievement(flow) -> None:
    await _mastered(flow, completion=DAY_NOON + 3600)
    await _sync(flow, [])
    assert len(await _stored(flow)) == 2


async def test_achievements_a_game_no_longer_has_are_removed_by_default(flow) -> None:
    await _mastered(flow, completion=DAY_NOON + 3600)
    await _sync(flow, [_row("0", DAY_NOON)])
    assert await _stored(flow) == {"0": DAY_NOON}


async def test_turning_the_setting_off_keeps_achievements_a_game_lost(flow) -> None:
    saved = await flow.client.put("/api/settings/scan", json={"remove_gone_achievements": False})
    assert saved.status_code == 200, saved.text
    assert saved.json()["remove_gone_achievements"] is False
    await _mastered(flow, completion=DAY_NOON + 3600)
    await _sync(flow, [_row("0", DAY_NOON)])
    assert await _stored(flow) == {"0": DAY_NOON, "1": DAY_NOON - 1}


async def test_new_achievements_take_mastered_off_but_keep_the_finish_day(flow) -> None:
    await _mastered(flow, completion=DAY_NOON)
    await _sync(flow, [_row("0", DAY_NOON), _row("1", DAY_NOON - 1), _row("dlc")])
    game = await _game(flow)
    assert game.status == GameStatus.PLAYED
    assert game.completion_date == DAY_NOON
    feed = (await flow.client.get("/api/calendar/games", params={"days": 36500})).json()
    assert any(e["kind"] == "game_finished" and e["date"] == DAY for e in feed), feed


async def test_mastered_set_by_hand_with_achievements_left_stays_mastered(flow) -> None:
    await _mastered(flow, completion=DAY_NOON, unlocked=(True, False))
    await _sync(flow, [_row("0", DAY_NOON), _row("1"), _row("dlc")])
    assert (await _game(flow)).status == GameStatus.MASTERED


async def test_the_calendar_reaches_a_year_ahead_and_the_week_can_start_on_any_day(flow) -> None:
    assert (await flow.client.get("/api/calendar", params={"days": 365})).status_code == 200
    saved = await flow.client.patch("/api/preferences", json={"calendar_week_start": 3})
    assert saved.json()["calendar_week_start"] == 3
    async with SessionLocal() as db:
        assert await db.scalar(select(Game.id).where(Game.id == flow.game_id))


async def test_marking_a_show_watched_on_its_page_ticks_off_its_episodes(flow) -> None:
    show = (
        await flow.client.post(
            "/api/tv/create",
            json={
                "title": "Dark",
                "status": "IN_PROGRESS",
                "seasons": [{"season_number": 1, "episode_count": 12}, {"season_number": 2}],
            },
        )
    ).json()
    done = await flow.client.patch(f"/api/tv/update/{show['id']}", json={"status": "WATCHED"})
    assert done.status_code == 200, done.text
    seasons = {s["season_number"]: s for s in done.json()["seasons"]}
    assert seasons[1]["episodes_watched"] == 12
    assert seasons[1]["status"] == "WATCHED"
    assert seasons[2]["episodes_watched"] == 0, "no episode count, nothing to tick"
    history = (await flow.client.get("/api/activity", params={"days": 36500})).json()
    assert any(e["event_type"] == "episodes_watched" and e["count"] == 12 for e in history)


async def test_marking_one_anime_season_watched_fills_that_season(flow) -> None:
    show = (
        await flow.client.post(
            "/api/anime/create",
            json={
                "title": "Frieren",
                "status": "IN_PROGRESS",
                "seasons": [
                    {"season_number": 1, "episode_count": 28},
                    {"season_number": 2, "episode_count": 10},
                ],
            },
        )
    ).json()
    first = next(s for s in show["seasons"] if s["season_number"] == 1)
    after = await flow.client.patch(
        f"/api/anime/{show['id']}/seasons/{first['id']}", json={"status": "WATCHED"}
    )
    assert after.status_code == 200, after.text
    seasons = {s["season_number"]: s for s in after.json()["seasons"]}
    assert seasons[1]["episodes_watched"] == 28
    assert seasons[2]["episodes_watched"] == 0


async def test_progress_typed_with_the_status_is_kept(flow) -> None:
    show = (
        await flow.client.post(
            "/api/tv/create",
            json={"title": "Lost", "seasons": [{"season_number": 1, "episode_count": 24}]},
        )
    ).json()
    season = show["seasons"][0]
    after = await flow.client.patch(
        f"/api/tv/{show['id']}/seasons/{season['id']}",
        json={"status": "WATCHED", "episodes_watched": 20},
    )
    assert after.json()["seasons"][0]["episodes_watched"] == 20
