"""A job that fails still counts as having run, so it is not retried every minute."""

from src.features import jobs


async def test_a_failed_airing_check_is_recorded_as_a_run(monkeypatch) -> None:
    recorded: list[tuple[str, dict]] = []

    async def failing(force):  # noqa: ARG001
        raise RuntimeError("AniList is down")

    async def record(job_id, result):
        recorded.append((job_id, result))

    monkeypatch.setattr(jobs, "check_airing_episodes", failing)
    monkeypatch.setattr(jobs, "record_run", record)
    jobs._airing_running = True
    await jobs._run_airing(force=False)

    assert recorded == [("airing_check", {"failed": True})]
    assert jobs._airing_running is False  # and it can run again at its next time


def test_a_failed_run_does_not_break_the_summary() -> None:
    assert jobs._summarize_airing({"failed": True}) == "0 checked, 0 not due yet"
