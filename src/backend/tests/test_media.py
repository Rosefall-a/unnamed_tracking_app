from src.helpers.media import classify_media, list_media, media_subdir, safe_filename


def test_classify_media_prefers_content_type() -> None:
    assert classify_media("image/png; charset=utf-8", "recording.mp4") == "screenshot"
    assert classify_media("video/webm", "image.png") == "clip"
    assert classify_media("audio/mpeg", "cover.jpg") == "soundtrack"


def test_classify_media_falls_back_to_extension() -> None:
    assert classify_media(None, "Screenshot.PNG") == "screenshot"
    assert classify_media("application/octet-stream", "clip.MKV") == "clip"
    assert classify_media(None, "theme.flac") == "soundtrack"
    assert classify_media(None, "document.pdf") is None


def test_media_subdir_maps_each_supported_kind() -> None:
    assert media_subdir("screenshot") == "screenshots"
    assert media_subdir("clip") == "clips"
    assert media_subdir("soundtrack") == "soundtrack"


def test_safe_filename_strips_paths_and_adds_unique_prefix() -> None:
    first = safe_filename("../../Screenshots/My File?.PNG")
    second = safe_filename("../../Screenshots/My File?.PNG")

    assert first.endswith("_My_File_.PNG")
    assert second.endswith("_My_File_.PNG")
    assert first != second


def test_list_media_returns_sorted_files_and_ignores_directories(tmp_path) -> None:
    (tmp_path / "b.png").write_bytes(b"b")
    (tmp_path / "a.png").write_bytes(b"a")
    (tmp_path / "nested").mkdir()

    assert list_media(tmp_path) == ["a.png", "b.png"]
    assert list_media(tmp_path / "missing") == []
