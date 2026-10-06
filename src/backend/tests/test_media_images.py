"""Posters and backdrops of movies, shows and anime are kept on this server."""

import io

import pytest
from PIL import Image

from src.api.routes import media_images
from src.helpers import remote_images
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


def _png(width: int = 1000, height: int = 1500) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (30, 90, 160)).save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
def downloads(monkeypatch, tmp_path):
    monkeypatch.setattr(media_images, "_DATA_ROOT", tmp_path)
    calls: list[str] = []

    def fake_download(url: str) -> bytes:
        calls.append(url)
        if "broken" in url:
            raise remote_images.RemoteImageError("status 404")
        return _png()

    monkeypatch.setattr(remote_images, "download_image", fake_download)
    return calls


async def _create(flow, kind: str, **fields) -> str:  # noqa: F811
    created = await flow.client.post(f"/api/{kind}/create", json={"title": "Heat", **fields})
    assert created.status_code == 201, created.text
    return created.json()["id"]


@pytest.mark.parametrize("kind", ["movie", "tv", "anime"])
async def test_poster_is_downloaded_once_and_served_small(flow, downloads, kind: str) -> None:
    item = await _create(flow, kind, poster_url="https://img.example.test/p.jpg")
    url = f"/api/media-image/{kind}/{item}/poster"

    first = await flow.client.get(url)
    assert first.status_code == 200
    assert first.headers["content-type"] == "image/jpeg"
    assert Image.open(io.BytesIO(first.content)).width == 400

    second = await flow.client.get(url)
    assert second.status_code == 200 and second.content == first.content
    assert downloads == ["https://img.example.test/p.jpg"]


async def test_backdrop_keeps_its_own_size(flow, downloads) -> None:
    item = await _create(flow, "movie", backdrop_url="https://img.example.test/b.jpg")
    response = await flow.client.get(f"/api/media-image/movie/{item}/backdrop")
    assert Image.open(io.BytesIO(response.content)).width == 1000  # smaller than 1920: kept as is


async def test_hero_uses_the_backdrop_or_else_the_poster(flow, downloads) -> None:
    both = await _create(flow, "movie", poster_url="https://img.example.test/p.jpg", backdrop_url="https://img.example.test/b.jpg")
    poster_only = await _create(flow, "movie", poster_url="https://img.example.test/only-p.jpg")
    await flow.client.get(f"/api/media-image/movie/{both}/hero")
    await flow.client.get(f"/api/media-image/movie/{poster_only}/hero")
    assert downloads == ["https://img.example.test/b.jpg", "https://img.example.test/only-p.jpg"]


async def test_changing_the_address_makes_a_fresh_copy(flow, downloads) -> None:
    item = await _create(flow, "movie", poster_url="https://img.example.test/old.jpg")
    await flow.client.get(f"/api/media-image/movie/{item}/poster")
    await flow.client.patch(f"/api/movie/update/{item}", json={"poster_url": "https://img.example.test/new.jpg"})
    await flow.client.get(f"/api/media-image/movie/{item}/poster")
    assert downloads == ["https://img.example.test/old.jpg", "https://img.example.test/new.jpg"]
    folder = media_images._DATA_ROOT / str(flow.user_id) / ".cache" / "media-images" / "movie"
    assert len(list(folder.glob("*.jpg"))) == 1  # the old copy was removed


async def test_a_failed_download_sends_the_browser_to_the_original(flow, downloads) -> None:
    item = await _create(flow, "movie", poster_url="https://img.example.test/broken.jpg")
    response = await flow.client.get(f"/api/media-image/movie/{item}/poster", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://img.example.test/broken.jpg"


async def test_missing_image_and_unknown_title_are_404(flow, downloads) -> None:
    item = await _create(flow, "movie")
    assert (await flow.client.get(f"/api/media-image/movie/{item}/poster")).status_code == 404
    other = "00000000-0000-0000-0000-000000000001"
    assert (await flow.client.get(f"/api/media-image/movie/{other}/poster")).status_code == 404
    assert (await flow.client.get(f"/api/media-image/game/{item}/poster")).status_code == 422


@pytest.mark.parametrize(
    ("host", "public"),
    [
        ("127.0.0.1", False),
        ("localhost", False),
        ("10.1.2.3", False),
        ("192.168.0.5", False),
        ("169.254.169.254", False),
        ("::1", False),
        ("0.0.0.0", False),
        ("93.184.216.34", True),
    ],
)
def test_only_public_hosts_are_fetched(host: str, public: bool) -> None:
    assert remote_images.is_public_host(host) is public


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/a.png", "http://127.0.0.1/a.png", "https:///x"])
def test_unsafe_addresses_are_refused(url: str) -> None:
    with pytest.raises(remote_images.RemoteImageError):
        remote_images.download_image(url)
