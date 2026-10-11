"""Achievement icons are kept lossless, and a larger copy can be made for the page."""

import io

import pytest
from PIL import Image

from src.helpers import remote_images


def _jpeg(size: int) -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", (size, size), (200, 120, 30))
    image.paste((20, 20, 20), (size // 4, size // 4, size * 3 // 4, size * 3 // 4))
    image.save(buffer, "JPEG", quality=90)
    return buffer.getvalue()


@pytest.fixture
def served(monkeypatch):
    def serve(data: bytes) -> None:
        monkeypatch.setattr(remote_images, "download_image", lambda _url: data)

    return serve


def test_a_small_icon_is_kept_at_its_own_size_as_png(tmp_path, served) -> None:
    served(_jpeg(64))
    target = remote_images.icon_cache_path(tmp_path, "https://x.test/i.jpg")
    remote_images.fetch_icon("https://x.test/i.jpg", target)
    with Image.open(target) as saved:
        assert saved.format == "PNG" and saved.size == (64, 64)


def test_a_big_icon_is_capped_not_blown_up(tmp_path, served) -> None:
    served(_jpeg(600))
    target = remote_images.icon_cache_path(tmp_path, "https://x.test/big.jpg")
    remote_images.fetch_icon("https://x.test/big.jpg", target)
    with Image.open(target) as saved:
        assert saved.size == (remote_images.ICON_LARGE, remote_images.ICON_LARGE)


def test_the_large_copy_is_made_from_the_small_one(tmp_path, served) -> None:
    served(_jpeg(64))
    small = remote_images.icon_cache_path(tmp_path, "https://x.test/i.jpg")
    large = remote_images.icon_cache_path(tmp_path, "https://x.test/i.jpg", large=True)
    remote_images.fetch_icon("https://x.test/i.jpg", small)
    remote_images.make_large_icon(small, large)
    assert small != large
    with Image.open(large) as made:
        assert made.format == "PNG" and made.size == (256, 256)
    with Image.open(small) as untouched:
        assert untouched.size == (64, 64)


def test_something_that_is_not_an_image_is_refused(tmp_path, served) -> None:
    served(b"<html>not an image</html>")
    with pytest.raises(remote_images.RemoteImageError):
        remote_images.fetch_icon("https://x.test/x", tmp_path / "x.png")
