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


def test_bulk_upload_routes_accept_the_files_field() -> None:
    # a shared File() default once made these demand a field named "file",
    # so every browser upload (which sends "files") came back 422
    import uuid
    from types import SimpleNamespace

    from fastapi.testclient import TestClient

    from src.api.routes.games import get_current_user
    from src.main import app

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid.uuid4())
    try:
        client = TestClient(app)
        for suffix in ("screenshots", "files/doc"):
            response = client.post(
                f"/api/game/{uuid.uuid4()}/{suffix}",
                files=[("files", ("a.png", b"x", "image/png"))],
                data={"last_modified": ["1700000000000"]},
            )
            assert response.status_code != 422, (suffix, response.text)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_ranged_file_response_serves_partial_content(tmp_path) -> None:
    from types import SimpleNamespace

    from src.helpers.range_response import ranged_file_response

    clip = tmp_path / "clip.mp4"
    clip.write_bytes(bytes(range(100)))

    def get(range_header):
        headers = {"range": range_header} if range_header else {}
        return ranged_file_response(SimpleNamespace(headers=headers), clip)

    whole = get(None)
    assert whole.status_code == 200 and whole.headers["accept-ranges"] == "bytes"

    first = get("bytes=0-9")
    assert first.status_code == 206
    assert first.headers["content-range"] == "bytes 0-9/100"
    assert first.headers["content-length"] == "10"

    # an open-ended range (what a player sends to find the length) and a suffix range
    assert get("bytes=90-").headers["content-range"] == "bytes 90-99/100"
    assert get("bytes=-5").headers["content-range"] == "bytes 95-99/100"

    refused = get("bytes=500-")
    assert refused.status_code == 416
    assert refused.headers["content-range"] == "bytes */100"
