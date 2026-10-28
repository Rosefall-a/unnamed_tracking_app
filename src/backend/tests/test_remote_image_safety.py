"""An address someone or something gave us is only fetched when it is a public
image: never this machine, the local network or a shared-address range, and a
redirect is checked like the first address."""

import pytest

from src.helpers import remote_images
from src.helpers.remote_images import RemoteImageError, download_image, is_public_host
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


@pytest.mark.parametrize(
    "host",
    ["127.0.0.1", "10.1.2.3", "192.168.0.9", "169.254.169.254", "172.16.5.5", "100.64.0.1", "0.0.0.0", "::1"],
)
def test_internal_and_special_addresses_are_not_public(host) -> None:
    assert not is_public_host(host)


def test_a_public_address_is_public() -> None:
    assert is_public_host("8.8.8.8")


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/a.png",
        "file:///etc/passwd",
        "http://127.0.0.1/a.png",
        "http://169.254.169.254/latest/meta-data/",
        "http://example.com:8080/a.png",  # not a web port
        "http://example.com:5432/a.png",
        "http:///a.png",
    ],
)
def test_unsafe_addresses_are_refused(url) -> None:
    with pytest.raises(RemoteImageError):
        download_image(url)


class _Redirect:
    status_code = 302
    headers = {"location": "http://169.254.169.254/latest/meta-data/"}

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def test_a_redirect_into_the_local_network_is_refused(monkeypatch) -> None:
    asked: list[str] = []
    monkeypatch.setattr(remote_images, "is_public_host", lambda host: host == "cdn.example.com")

    def fake_get(url, **_kw):
        asked.append(url)
        return _Redirect()

    monkeypatch.setattr(remote_images.requests, "get", fake_get)
    with pytest.raises(RemoteImageError):
        download_image("https://cdn.example.com/a.png")
    assert asked == ["https://cdn.example.com/a.png"]  # the internal address was never requested


async def test_the_from_url_route_refuses_an_internal_address(flow) -> None:  # noqa: F811
    response = await flow.client.post(
        f"{flow.game}/assets/key_art/from-url", json={"url": "http://127.0.0.1:8000/api/auth/me"}
    )
    assert response.status_code == 400
    assert "127.0.0.1" not in response.text
