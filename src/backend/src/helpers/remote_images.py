"""Keeping a local copy of a poster or backdrop that lives on another server.

Movies, shows and anime store the address of their artwork on TMDB or AniList.
This downloads each one once, shrinks it to what a page shows, and keeps it on
disk, so after the first time nothing waits on someone else's server.

The address is whatever was saved on the title, so it is checked before it is
fetched: only http(s), only public hosts (never this machine or the local
network), no redirects, and a size limit.
"""

import hashlib
import io
import ipaddress
import os
import socket
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import requests
from PIL import Image, ImageFilter, UnidentifiedImageError

MAX_BYTES = 15 * 1024 * 1024
_TIMEOUT = (5, 15)  # connect, read
_QUALITY = 82
_BACKDROP = (26, 26, 26)  # what a see-through image is laid over


class RemoteImageError(Exception):
    """The image could not be fetched or is not one we will keep."""


def is_public_host(host: str) -> bool:
    """True when every address `host` resolves to is on the public internet."""
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            return False
    return True


def download_image(url: str) -> bytes:
    """The bytes at `url`, or RemoteImageError if it is not a safe, small image."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise RemoteImageError("not an http(s) address")
    if not is_public_host(parts.hostname):
        raise RemoteImageError("not a public host")
    try:
        with requests.get(
            url,
            stream=True,
            timeout=_TIMEOUT,
            allow_redirects=False,
            headers={"User-Agent": "unnamed-tracking-app/1.0 (image cache)"},
        ) as response:
            if response.status_code != 200:
                raise RemoteImageError(f"status {response.status_code}")
            declared = response.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > MAX_BYTES:
                raise RemoteImageError("too large")
            data = bytearray()
            for chunk in response.iter_content(64 * 1024):
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    raise RemoteImageError("too large")
    except requests.RequestException as exc:
        raise RemoteImageError(str(exc)) from exc
    return bytes(data)


def save_shrunk(data: bytes, target: Path, width: int) -> None:
    """Write `data` as a JPEG at most `width` pixels wide to `target`."""
    try:
        with Image.open(io.BytesIO(data)) as opened:
            has_alpha = "A" in opened.getbands() or "transparency" in opened.info
            image = opened.convert("RGBA" if has_alpha else "RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise RemoteImageError("not an image") from exc
    if image.width > width:
        height = max(1, round(image.height * width / image.width))
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    if has_alpha:
        flat = Image.new("RGB", image.size, _BACKDROP)
        flat.paste(image, mask=image.getchannel("A"))
        image = flat
    target.parent.mkdir(parents=True, exist_ok=True)
    # written beside the target then moved into place, so a request that
    # arrives mid-write never reads half a file
    handle, temp_name = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    os.close(handle)
    try:
        image.save(temp_name, format="JPEG", quality=_QUALITY)
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def cache_path(cache_root: Path, media_type: str, item_id: str, which: str, url: str) -> Path:
    """Where the local copy of one title's poster or backdrop lives. The address
    is part of the name, so changing it on the title makes a fresh copy."""
    digest = hashlib.sha1(url.encode("utf-8"), usedforsecurity=False).hexdigest()[:10]
    return cache_root / "media-images" / media_type / f"{item_id}-{which}-{digest}.jpg"


def fetch_and_store(url: str, target: Path, width: int) -> None:
    """Download `url`, keep it at `target`, and drop older copies of the same
    picture (from an address the title used to have)."""
    save_shrunk(download_image(url), target, width)
    prefix = target.name.rsplit("-", 1)[0] + "-"
    for old in target.parent.glob(f"{prefix}*.jpg"):
        if old != target:
            old.unlink(missing_ok=True)


ICON_LARGE = 256


def icon_cache_path(cache_root: Path, url: str, large: bool = False) -> Path:
    """Where the local copy of an achievement icon lives. Icons are the same for
    every player, so they are kept once, named by their address. `large` is the
    bigger copy made for the achievement's own page."""
    digest = hashlib.sha1(url.encode("utf-8"), usedforsecurity=False).hexdigest()
    return cache_root / "achievement-icons" / f"{digest}{'-large' if large else ''}.png"


def _write_png(image: Image.Image, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=target.parent, suffix=".tmp")
    os.close(handle)
    try:
        image.save(temp_name, format="PNG", optimize=True)
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def fetch_icon(url: str, target: Path) -> None:
    """Keep an achievement icon exactly as the provider made it, as a lossless PNG.
    Steam's are 64 px JPEGs; saving them as JPEG again would damage them twice."""
    try:
        with Image.open(io.BytesIO(download_image(url))) as opened:
            image = opened.convert("RGBA")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise RemoteImageError("not an image") from exc
    if image.width > ICON_LARGE:
        image = image.resize((ICON_LARGE, round(image.height * ICON_LARGE / image.width)), Image.Resampling.LANCZOS)
    _write_png(image, target)


def make_large_icon(source: Path, target: Path) -> None:
    """A 256 px copy of a small icon for the achievement's page. Enlarged with
    Lanczos and a light sharpen, which keeps edges cleaner than the browser's
    own stretching; shown at half that size it is downscaled, so it stays crisp.
    It cannot add detail the provider never had."""
    with Image.open(source) as opened:
        image = opened.convert("RGBA")
    if image.width < ICON_LARGE:
        height = round(image.height * ICON_LARGE / image.width)
        image = image.resize((ICON_LARGE, height), Image.Resampling.LANCZOS)
        rgb = image.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1.4, percent=110, threshold=2))
        rgb.putalpha(image.getchannel("A"))
        image = rgb
    _write_png(image, target)
