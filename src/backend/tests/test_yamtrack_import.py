from src.features.imports.yamtrack import YamtrackImportError, parse_yamtrack


HEADER = (
    "media_id,source,media_type,title,image,season_number,episode_number,score,status,notes,"
    "start_date,end_date,progress,created_at,progressed_at\n"
)


def test_yamtrack_parser_keeps_tv_episode_progress_and_movie_tracking_data():
    raw = (
        HEADER
        + '100,tmdb,tv,Example Show,,,,8.5,In progress,Good show,2025-01-01 00:00:00+00:00,,20,,\n'
        + '100,tmdb,season,,"",1,,Completed,,,,,,\n'
        + '100,tmdb,episode,,"",1,1,,Completed,,2025-01-02 00:00:00+00:00,2025-01-02 01:00:00+00:00,0,,\n'
        + '100,tmdb,episode,,"",1,2,,Completed,,2025-01-03 00:00:00+00:00,2025-01-03 01:00:00+00:00,0,,\n'
        + '200,tmdb,movie,Example Movie,, , ,9.0,Completed,Great,2025-02-01 00:00:00+00:00,2025-02-01 01:00:00+00:00,,,\n'
        + '300,igdb,game,Unsupported Game,,,,,Completed,,,,,,\n'
    ).encode()

    entries, skipped = parse_yamtrack(raw)

    assert len(entries) == 2
    assert skipped == 1

    show = next(item for item in entries if item.item.kind == "tv")
    movie = next(item for item in entries if item.item.kind == "movie")
    assert show.item.title == "Example Show"
    assert str(show.item.rating) == "8.5"
    assert show.episodes_by_season[1] == {1, 2}
    assert 1 in show.season_completed
    assert movie.item.status == "WATCHED"
    assert str(movie.item.rating) == "9.0"


def test_yamtrack_parser_rejects_non_yamtrack_csv():
    try:
        parse_yamtrack(b"title,status\nExample,Completed\n")
    except YamtrackImportError as exc:
        assert "YamTrack export" in str(exc)
    else:
        raise AssertionError("expected YamtrackImportError")
