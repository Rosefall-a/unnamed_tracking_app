""" "Last touched" comes from what you did, not from the server editing a record:
something done today keeps its time, and a past day filled in later (an import,
an old watch logged now) counts as that day."""

import time
import uuid
from datetime import UTC, date, datetime, timedelta

from src.database.models.media_extras import ActivityEventType, ActivityLog, MediaType
from src.database.session import SessionLocal
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


async def _log(user_id, media_id, day: date, updated_at: int, kind=MediaType.TV) -> None:
    async with SessionLocal() as db:
        db.add(
            ActivityLog(
                user_id=user_id,
                media_type=kind,
                media_id=media_id,
                media_title="Show",
                event_type=ActivityEventType.EPISODES_WATCHED,
                event_date=day,
                updated_at=updated_at,
            )
        )
        await db.commit()


async def test_last_touched_is_when_you_did_it(flow) -> None:  # noqa: F811
    now = int(time.time())
    today = datetime.fromtimestamp(now, UTC).date()
    watched_today, filled_in, untouched = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    await _log(flow.user_id, watched_today, today, now)
    # an old watch typed in today counts as its own day, at noon
    old_day = today - timedelta(days=200)
    await _log(flow.user_id, filled_in, old_day, now)
    await _log(flow.user_id, filled_in, old_day - timedelta(days=5), now - 10)

    response = await flow.client.get("/api/activity/last-touched")
    assert response.status_code == 200, response.text
    touched = response.json()
    assert touched[f"tv:{watched_today}"] == now
    noon = int(datetime.combine(old_day, datetime.min.time().replace(hour=12), UTC).timestamp())
    assert touched[f"tv:{filled_in}"] == noon
    # nothing done with it, so it is not there at all
    assert f"tv:{untouched}" not in touched
