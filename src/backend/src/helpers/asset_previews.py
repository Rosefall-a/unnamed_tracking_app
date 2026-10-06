"""Smaller copies of a game's artwork for showing on screen.

A game's banner is stored as a 3840x1240 PNG, often 5 to 10 MB. The page's
hero needs a fraction of that, so a resized JPEG is made the first time one is
asked for and kept in a cache folder, and rebuilt if the original changes.
"""

import os
import tempfile
from pathlib import Path

from PIL import Image

_BACKDROP = (26, 26, 26)  # what a see-through PNG is laid over (the page's dark)
_QUALITY = 82

# the sizes the app asks for: the page hero, the library's preview panel, and
# the poster on a game's page
STANDARD_WIDTHS: dict[str, tuple[int, ...]] = {"banner": (1920, 800), "key_art": (400,)}


def preview_path(cache_root: Path, game_id: str, kind: str, width: int) -> Path:
    """Where the resized copy of one game's asset lives."""
    return cache_root / "asset-previews" / game_id / f"{kind}-{width}.jpg"


def ensure_preview(source: Path, target: Path, width: int) -> tuple[Path, str]:
    """The file to send for `source` at most `width` pixels wide, and its media
    type. An image already that small (or smaller) is sent as it is."""
    if target.is_file() and target.stat().st_mtime >= source.stat().st_mtime:
        return target, "image/jpeg"
    with Image.open(source) as opened:
        if opened.width <= width:
            return source, "image/png"
        has_alpha = "A" in opened.getbands()
        image = opened.convert("RGBA" if has_alpha else "RGB")
    height = max(1, round(image.height * width / image.width))
    image = image.resize((width, height), Image.Resampling.BILINEAR, reducing_gap=2.0)
    if has_alpha:
        flat = Image.new("RGB", image.size, _BACKDROP)
        flat.paste(image, mask=image.getchannel("A"))
    else:
        flat = image
    target.parent.mkdir(parents=True, exist_ok=True)
    # written beside the target then moved into place, so a request that
    # arrives mid-write never reads half a file
    handle, temp_name = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    os.close(handle)
    try:
        flat.save(temp_name, format="JPEG", quality=_QUALITY)
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return target, "image/jpeg"


def make_standard_previews(asset_path: Path, kind: str, game_id: str) -> None:
    """Make the sizes the app asks for right after artwork is saved, so the first
    time a game is opened they are already there. `asset_path` is
    <data>/<user>/games/<folder>/<file>; the cache sits beside `games`."""
    cache_root = asset_path.parents[2] / ".cache"
    for width in STANDARD_WIDTHS.get(kind, ()):
        ensure_preview(asset_path, preview_path(cache_root, game_id, kind, width), width)
