"""Where local copies of a library's other pictures live: episode stills, and
the pictures and short clips inside game descriptions (Steam's "About this
game" has both). Kept under the owner's .cache folder like posters, so they
can always be fetched again and never need backing up."""

from __future__ import annotations

import hashlib
import html
import re
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from src.helpers.remote_images import download_file, fetch_and_store

# a still shows about as wide as a poster
STILL_WIDTH = 400
# Steam's description clips are a few MB; anything far bigger is not one
CLIP_LIMIT = 60 * 1024 * 1024
PICTURE_LIMIT = 15 * 1024 * 1024
_PICTURE_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
_CLIP_TYPES = {".mp4", ".webm"}

_VIDEO = re.compile(r"<video\b([^>]*)>(.*?)</video>", re.IGNORECASE | re.DOTALL)
_IMG = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*\"([^\"]+)\"", re.IGNORECASE)
_POSTER = re.compile(r"\bposter\s*=\s*\"([^\"]+)\"", re.IGNORECASE)
_SOURCE = re.compile(
    r"<source\b[^>]*?\bsrc\s*=\s*\"([^\"]+)\"(?:[^>]*?\btype\s*=\s*\"([^\"]*)\")?", re.IGNORECASE
)


def _online(url: str) -> bool:
    return url.startswith(("http://", "https://"))


def _suffix(url: str) -> str:
    return Path(urlsplit(url).path).suffix.lower()


def description_files(description: str | None) -> list[str]:
    """Every picture and clip a description shows, in the order it shows them.
    A clip Steam gives as both webm and mp4 keeps only the mp4, which every
    browser plays, so one copy is saved instead of two. The page shows the
    same pick (frontend utils/localPictures.ts)."""
    if not description:
        return []
    found: list[str] = []
    for match in _IMG.finditer(_VIDEO.sub("", description)):
        found.append(html.unescape(match.group(1)))
    for video in _VIDEO.finditer(description):
        poster = _POSTER.search(video.group(1))
        if poster:
            found.append(html.unescape(poster.group(1)))
        sources = [html.unescape(m.group(1)) for m in _SOURCE.finditer(video.group(2))]
        mp4 = [u for u in sources if _suffix(u) == ".mp4"]
        found.extend(mp4[:1] or sources[:1])
    unique: list[str] = []
    for url in found:
        if _online(url) and url not in unique:
            unique.append(url)
    return unique


def _name(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8"), usedforsecurity=False).hexdigest()[:24]


def description_file_path(cache_root: Path, url: str) -> Path:
    suffix = _suffix(url)
    if suffix not in _PICTURE_TYPES | _CLIP_TYPES:
        suffix = ".img"
    return cache_root / "page-files" / f"{_name(url)}{suffix}"


def still_path(cache_root: Path, url: str) -> Path:
    return cache_root / "episode-stills" / f"{_name(url)}.jpg"


def cache_root(media_root: Path, user_id: UUID | str) -> Path:
    return media_root / str(user_id) / ".cache"


def is_clip(path: Path) -> bool:
    return path.suffix in _CLIP_TYPES


def fetch_description_file(url: str, target: Path) -> None:
    """Saved exactly as the site sends it, so an animated picture keeps moving
    and a clip is not re-encoded."""
    if is_clip(target):
        download_file(url, target, CLIP_LIMIT, ("video/",))
    else:
        download_file(url, target, PICTURE_LIMIT, ("image/",))


def fetch_still(url: str, target: Path) -> None:
    fetch_and_store(url, target, STILL_WIDTH)
