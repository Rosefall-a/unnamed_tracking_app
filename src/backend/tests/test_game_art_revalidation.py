"""Art is kept by the browser (an hour, or for good at an address with `?v=`), and a
picture replaced under the same address is sent again once the keeping runs out."""

import io

from PIL import Image

from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


def _png(colour) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (600, 900), colour).save(buffer, format="PNG")
    return buffer.getvalue()


async def test_replaced_art_is_sent_again_and_unchanged_art_is_not_modified(flow) -> None:
    folder = flow.tmp / str(flow.user_id) / "games" / "Flow"
    folder.mkdir(parents=True)
    art = folder / "key_art.png"
    art.write_bytes(_png("red"))
    url = f"{flow.game}/assets/key_art"

    first = await flow.client.get(url)
    assert first.status_code == 200
    assert first.headers["cache-control"] == "private, max-age=3600, must-revalidate"
    tag = first.headers["etag"]

    again = await flow.client.get(url, headers={"If-None-Match": tag})
    assert again.status_code == 304 and not again.content

    art.write_bytes(_png("blue"))  # the cover is replaced under the same address
    changed = await flow.client.get(url, headers={"If-None-Match": tag})
    assert changed.status_code == 200
    assert changed.headers["etag"] != tag
    assert changed.content == art.read_bytes()


async def test_an_address_with_a_version_is_kept_for_good(flow) -> None:
    folder = flow.tmp / str(flow.user_id) / "games" / "Flow"
    folder.mkdir(parents=True)
    (folder / "key_art.png").write_bytes(_png("red"))
    versioned = await flow.client.get(f"{flow.game}/assets/key_art?v=1791755433000")
    assert versioned.headers["cache-control"] == "private, max-age=31536000, immutable"


async def test_a_placeholder_is_never_kept(flow) -> None:
    placeholder = await flow.client.get(f"{flow.game}/assets/key_art")
    assert placeholder.status_code == 200
    assert placeholder.headers["content-type"].startswith("image/svg")
    assert placeholder.headers["cache-control"] == "private, no-cache"
