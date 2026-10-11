"""Replacing a game's art under the same address shows up at once: the browser asks
every time, and an unchanged picture answers "not modified" instead of being sent."""

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
    assert first.headers["cache-control"] == "private, no-cache"
    tag = first.headers["etag"]

    again = await flow.client.get(url, headers={"If-None-Match": tag})
    assert again.status_code == 304 and not again.content

    art.write_bytes(_png("blue"))  # the cover is replaced under the same address
    changed = await flow.client.get(url, headers={"If-None-Match": tag})
    assert changed.status_code == 200
    assert changed.headers["etag"] != tag
    assert changed.content == art.read_bytes()
