"""Every picture a library shows can be saved here so it can be viewed offline."""

from pathlib import Path

from src.database.models.achievement import Achievement
from src.database.session import SessionLocal
from src.features import offline_pictures
from src.helpers import image_prefetch
from src.helpers.remote_images import RemoteImageError
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


async def test_missing_pictures_are_counted_saved_and_a_failure_is_left(
    flow, tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(image_prefetch, "MEDIA_ROOT", tmp_path / "users")
    monkeypatch.setattr(image_prefetch, "ICON_ROOT", tmp_path / "cache")
    # nothing is downloaded while the rows are written
    monkeypatch.setattr(image_prefetch, "_semaphore", None)
    monkeypatch.setattr(image_prefetch, "_icon_semaphore", None)
    created = await flow.client.post(
        "/api/movie/create",
        json={
            "title": "Heat",
            "poster_url": "https://image.example/poster.jpg",
            "backdrop_url": "https://image.example/broken.jpg",
        },
    )
    assert created.status_code in (200, 201), created.text
    async with SessionLocal() as db:
        db.add(
            Achievement(
                game_id=flow.game_id,
                provider="Steam",
                external_id="1",
                name="One",
                icon_url="https://image.example/icon.png",
            )
        )
        await db.commit()

    missing = await offline_pictures.count_missing(flow.user_id)
    assert missing == {"movie": 2, "tv": 0, "anime": 0, "icon": 1, "still": 0, "page": 0}

    def fake_fetch(url: str, target: Path, _how) -> None:
        if "broken" in url:
            raise RemoteImageError("no answer")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"picture")

    monkeypatch.setattr(offline_pictures, "_fetch", fake_fetch)
    seen: list[tuple[int, int]] = []
    result = await offline_pictures.save_missing(
        flow.user_id, lambda done, total: seen.append((done, total))
    )
    assert result == {"checked": 3, "pictures": 2, "failed": 1}
    assert seen[-1] == (3, 3)
    assert await offline_pictures.count_missing(flow.user_id) == {
        "movie": 1,
        "tv": 0,
        "anime": 0,
        "icon": 0,
        "still": 0,
        "page": 0,
    }, "the one that failed is tried again next time, the saved ones stay"


def test_an_icon_steam_moved_is_fetched_from_its_current_host(monkeypatch, tmp_path) -> None:
    import io

    from PIL import Image

    from src.helpers import remote_images

    old = "https://steamcdn-a.akamaihd.net/steamcommunity/public/images/apps/10/abc123.jpg"
    asked: list[str] = []
    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), "red").save(buffer, "JPEG")

    def fake_download(url: str) -> bytes:
        asked.append(url)
        if "steamcdn-a" in url:
            raise RemoteImageError("status 404")
        return buffer.getvalue()

    monkeypatch.setattr(remote_images, "download_image", fake_download)
    remote_images.fetch_icon(old, tmp_path / "icon.png")
    assert asked[-1] == (
        "https://shared.akamai.steamstatic.com/community_assets/images/apps/10/abc123.jpg"
    )
    assert (tmp_path / "icon.png").is_file()
    assert remote_images.current_steam_icon("https://example.com/a.jpg") is None


DESCRIPTION = (
    '<p>Hi</p><img src="https://shared.example/a.jpg?t=1&amp;x=2">'
    '<video class="bb_img" autoplay poster="https://shared.example/c.poster.avif">'
    '<source src="https://shared.example/c.webm" type="video/webm">'
    '<source src="https://shared.example/c.mp4" type="video/mp4"></video>'
)


def test_a_description_keeps_its_pictures_and_one_copy_of_each_clip() -> None:
    from src.helpers.local_copies import description_files

    assert description_files(DESCRIPTION) == [
        "https://shared.example/a.jpg?t=1&x=2",
        "https://shared.example/c.poster.avif",
        "https://shared.example/c.mp4",
    ]
    assert description_files(None) == []


async def test_description_files_and_stills_are_served_from_disk_and_only_your_own(
    flow, tmp_path, monkeypatch
) -> None:
    from src.api.routes import local_pictures
    from src.database.models.game import Game
    from src.helpers import local_copies

    monkeypatch.setattr(image_prefetch, "MEDIA_ROOT", tmp_path / "users")
    monkeypatch.setattr(image_prefetch, "_semaphore", None)
    async with SessionLocal() as db:
        game = await db.get(Game, flow.game_id)
        game.description = DESCRIPTION
        await db.commit()
    fetched: list[str] = []

    def fake_file(url: str, target: Path) -> None:
        fetched.append(url)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"clip" if url.endswith(".mp4") else b"picture")

    monkeypatch.setattr(local_pictures, "fetch_description_file", fake_file)
    monkeypatch.setattr(local_pictures, "fetch_still", fake_file)
    clip = await flow.client.get(
        f"/api/game/{flow.game_id}/page-file", params={"u": "https://shared.example/c.mp4"}
    )
    assert clip.status_code == 200 and clip.content == b"clip"
    assert clip.headers["content-type"] == "video/mp4"
    again = await flow.client.get(
        f"/api/game/{flow.game_id}/page-file", params={"u": "https://shared.example/c.mp4"}
    )
    assert again.status_code == 200 and fetched == ["https://shared.example/c.mp4"]
    # a player skipping ahead asks for part of the clip and gets just that
    part = await flow.client.get(
        f"/api/game/{flow.game_id}/page-file",
        params={"u": "https://shared.example/c.mp4"},
        headers={"Range": "bytes=1-2"},
    )
    assert part.status_code == 206 and part.content == b"li"
    assert part.headers["content-range"] == "bytes 1-2/4"
    stranger = await flow.client.get(
        f"/api/game/{flow.game_id}/page-file", params={"u": "http://169.254.169.254/latest"}
    )
    assert stranger.status_code == 404, "only an address in the description is fetched"

    show = (
        await flow.client.post(
            "/api/tv/create",
            json={"title": "Dark", "seasons": [{"season_number": 1, "episode_count": 1}]},
        )
    ).json()
    from src.database.models.tv_show import TVEpisode

    async with SessionLocal() as db:
        episode = TVEpisode(
            season_id=show["seasons"][0]["id"],
            episode_number=1,
            title="Secrets",
            still_url="https://image.example/still.jpg",
        )
        db.add(episode)
        await db.commit()
        episode_id = episode.id
    assert (await offline_pictures.count_missing(flow.user_id))["still"] == 1
    still = await flow.client.get(f"/api/episode-still/tv/{episode_id}")
    assert still.status_code == 200 and still.content == b"picture"
    assert (await offline_pictures.count_missing(flow.user_id))["still"] == 0
    assert local_copies.still_path(
        local_copies.cache_root(tmp_path / "users", flow.user_id),
        "https://image.example/still.jpg",
    ).is_file()
