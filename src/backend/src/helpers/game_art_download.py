"""Downloading a game's artwork from a web address into its folder."""

import asyncio
import json
import re
from collections.abc import AsyncIterator, Iterable
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

import requests
from PIL import Image, ImageChops, ImageStat

from src.core.config import settings
from src.features.metadata.games.igdb import IGDBClient
from src.features.metadata.games.steam_grid_db import SteamGridDBClient, SteamGridDBError
from src.helpers.remote_images import RemoteImageError, download_image
from src.helpers.save_game_asset import ASSET_FILENAMES, DATA_ROOT, AssetKind, save_game_asset

_ART_KINDS: tuple[AssetKind, ...] = ("key_art", "banner", "logo", "icon")
_STORE_ITEMS_URL = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/"
_STORE_ASSET_HOST = "https://shared.akamai.steamstatic.com/store_item_assets/"
_COMMUNITY_ICON_HOST = "https://cdn.akamai.steamstatic.com/steamcommunity/public/images/apps"
_SGDB_COVER_SIZES = "600x900,660x930"
# a cover is 2:3 (0.67); a square or wide image is not used for one
_MOST_COVER_WIDTH = 0.85
# how far apart two copies of a picture can be, per colour channel out of 255,
# and still be the same picture (one being a resized or recompressed copy)
_SAME_PICTURE = 2.0
_COMPARE_SIZE = (60, 90)
_SGDB_IMAGE_TYPES: dict[AssetKind, str] = {
    "key_art": "grids",
    "banner": "heroes",
    "logo": "logos",
    "icon": "icons",
}


# Steam's CDN asset naming convention is stable and public (used by Playnite,
# LaunchBox, etc.) — since a Steam library sync already knows the exact
# appid, art can come straight from here instead of a text search that might
# match the wrong game. download_asset silently no-ops on a 404, so trying
# a URL that doesn't exist for an older game is harmless.
def steam_cdn_art_urls(app_id: int) -> dict[AssetKind, str]:
    base = f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}"
    return {
        "key_art": f"{base}/library_600x900.jpg",
        "banner": f"{base}/library_hero.jpg",
        "logo": f"{base}/logo.png",
    }


def _is_generated_capsule(filename: str) -> bool:
    """A game whose makers uploaded no portrait gets one Steam builds itself from
    the hero and logo, called portrait.png: mostly empty space around a small logo."""
    return filename.rsplit("/", 1)[-1].lower().startswith("portrait")


def steam_store_art(app_id: int) -> tuple[dict[AssetKind, str], str | None]:
    """The art addresses from the store's own item list, and separately the cover
    Steam generated when that is all it has. Empty when Steam does not answer."""
    query = {
        "ids": [{"appid": app_id}],
        "context": {"language": "english", "country_code": "US"},
        "data_request": {"include_assets": True},
    }
    try:
        response = requests.get(
            _STORE_ITEMS_URL, params={"input_json": json.dumps(query)}, timeout=10
        )
        response.raise_for_status()
        items = response.json().get("response", {}).get("store_items") or []
    except (requests.RequestException, ValueError, AttributeError):
        return {}, None
    assets = (items[0].get("assets") or {}) if items else {}
    url_format = assets.get("asset_url_format")
    if not url_format:
        return {}, None

    def url(filename: str | None) -> str | None:
        return _STORE_ASSET_HOST + url_format.replace("${FILENAME}", filename) if filename else None

    capsule = assets.get("library_capsule_2x") or assets.get("library_capsule")
    generated = _is_generated_capsule(capsule) if capsule else False
    found: dict[AssetKind, str | None] = {
        "key_art": None if generated else url(capsule),
        "banner": url(assets.get("library_hero_2x") or assets.get("library_hero")),
    }
    if assets.get("community_icon"):
        found["icon"] = f"{_COMMUNITY_ICON_HOST}/{app_id}/{assets['community_icon']}.jpg"
    urls = {kind: address for kind, address in found.items() if address}
    return urls, url(capsule) if generated else None


def steam_store_art_urls(app_id: int) -> dict[AssetKind, str]:
    """Art of newer Steam games lives under a hashed path that the fixed names
    above cannot reach, so its real address comes from the store's own item list."""
    return steam_store_art(app_id)[0]


def _is_portrait(image: bytes) -> bool:
    """Saving stretches art to fit, so anything but a tall image makes a mangled
    cover. One that cannot be read is left for the save to refuse."""
    try:
        with Image.open(BytesIO(image)) as opened:
            width, height = opened.size
    except OSError:
        return True
    return width / height <= _MOST_COVER_WIDTH


async def download_asset(url: str, game_id: UUID, asset_kind: AssetKind) -> bool:
    """Best-effort — mirrors games.py's download_game_asset route but never
    raises, since one bad art URL must not fail an entire library sync.
    Returns whether it actually saved something, so callers can fall back
    to a different URL."""
    try:
        # checked like any address that is not ours: public hosts only, a size cap
        image = await asyncio.to_thread(download_image, url)
    except RemoteImageError:
        return False
    if asset_kind == "key_art" and not _is_portrait(image):
        return False
    try:
        await save_game_asset(image, game_id, asset_kind)
        return True
    except (OSError, ValueError):
        return False


def wanted_art(game: Any, scan_settings: Any = None) -> list[AssetKind]:
    """The artwork this game has no file for, leaving out what the person chose
    not to save and what they locked. Art that exists is never replaced."""
    if not game.folder_location:
        return []
    folder = DATA_ROOT / str(game.user_id) / "games" / game.folder_location
    return [
        kind
        for kind in _ART_KINDS
        if not (folder / ASSET_FILENAMES[kind]).is_file()
        and kind not in (game.locked_fields or [])
        and (scan_settings is None or getattr(scan_settings, f"save_{kind}", True))
    ]


def _name_key(title: str) -> str:
    return re.sub(r"[\W_]+", "", title).lower()


def _steamgriddb_game_id(
    client: SteamGridDBClient, app_id: int | None, title: str | None
) -> int | None:
    """By Steam app id, which is unambiguous; a newer game is often only listed
    by name, and then only an exact name counts, so another game's art is never
    used."""
    if app_id:
        try:
            found = client.get_game_by_steam_appid(app_id)
        except SteamGridDBError:
            found = None
        if found and found.get("id"):
            return int(found["id"])
    if not title or title.startswith("Steam app "):
        return None
    for hit in client.search_games(title, limit=5):
        if hit.get("id") and _name_key(str(hit.get("name") or "")) == _name_key(title):
            return int(hit["id"])
    return None


class _ArtSources:
    """Where each kind of art can come from, best first. Each source is only
    asked once something before it has failed."""

    def __init__(
        self,
        app_id: int | None,
        title: str | None,
        api_key: str | None,
        header_image: str | None,
        igdb_keys: tuple[str | None, str | None] = (None, None),
    ) -> None:
        self._app_id, self._title, self._api_key = app_id, title, api_key
        self._header_image = header_image
        self._igdb_keys = igdb_keys
        self._store: dict[AssetKind, str] | None = None
        self._generated_cover: str | None = None
        self._client: SteamGridDBClient | None = None
        self._sgdb_id: int | None = None
        self._sgdb_asked = False

    async def _store_url(self, kind: AssetKind) -> str | None:
        if self._app_id is None:
            return None
        if self._store is not None:
            return self._store.get(kind)
        store, self._generated_cover = await asyncio.to_thread(steam_store_art, self._app_id)
        self._store = store
        return store.get(kind)

    async def _igdb_cover(self) -> str | None:
        """IGDB's box art, for a game listed under exactly this name."""
        client_id, client_secret = self._igdb_keys
        if not (client_id and client_secret and self._title):
            return None
        try:
            client = IGDBClient(client_id=client_id, client_secret=client_secret)
            results = await asyncio.to_thread(client.search, self._title, 5)
        except Exception:  # best-effort: one odd answer must not fail a whole import
            return None
        wanted = _name_key(self._title)
        for result in results:
            cover = result.get("cover_url")
            if cover and _name_key(str(result.get("name") or "")) == wanted:
                return str(cover).replace("t_cover_big", "t_cover_big_2x")
        return None

    async def _sgdb_urls(self, kind: AssetKind) -> list[str]:
        if not self._api_key:
            return []
        try:
            if not self._sgdb_asked:
                self._sgdb_asked = True
                self._client = SteamGridDBClient(self._api_key)
                self._sgdb_id = await asyncio.to_thread(
                    _steamgriddb_game_id, self._client, self._app_id, self._title
                )
            if self._client is None or self._sgdb_id is None:
                return []
            images = await asyncio.to_thread(
                self._client.get_game_images,
                self._sgdb_id,
                _SGDB_IMAGE_TYPES[kind],
                dimensions=_SGDB_COVER_SIZES if kind == "key_art" else None,
            )
        except Exception:  # best-effort: one odd answer must not fail a whole import
            return []
        images.sort(key=lambda image: image.score if image.score is not None else -1, reverse=True)
        return [image.url for image in images[:3] if image.url]

    async def _cover_urls(self) -> AsyncIterator[str]:
        """The store's own portrait is what the makers uploaded. The old fixed
        address is often a small out-of-date copy, and Steam's generated one is
        the worst of all, so real covers from elsewhere come before both."""
        if self._app_id:
            makers_cover = await self._store_url("key_art")
            if makers_cover:
                yield makers_cover
        for address in await self._sgdb_urls("key_art"):
            yield address
        igdb_cover = await self._igdb_cover()
        if igdb_cover:
            yield igdb_cover
        if self._app_id:
            fixed = steam_cdn_art_urls(self._app_id).get("key_art")
            if fixed:
                yield fixed
            if self._generated_cover:
                yield self._generated_cover

    async def urls(self, kind: AssetKind) -> AsyncIterator[str]:
        if kind == "key_art":
            async for address in self._cover_urls():
                yield address
            return
        if self._app_id:
            fixed = steam_cdn_art_urls(self._app_id).get(kind)
            if fixed:
                yield fixed
            # Steam's own icon is 32 pixels: only used when nothing better exists
            if kind != "icon":
                from_store = await self._store_url(kind)
                if from_store:
                    yield from_store
        # a wide header would be cropped badly into the portrait cover, so it is
        # only ever a banner
        if kind == "banner" and self._header_image:
            yield self._header_image
        for address in await self._sgdb_urls(kind):
            yield address
        if kind == "icon" and self._app_id:
            tiny_icon = await self._store_url(kind)
            if tiny_icon:
                yield tiny_icon


async def fill_art(
    game_id: UUID,
    kinds: Iterable[AssetKind],
    app_id: int | None,
    title: str | None,
    steamgriddb_api_key: str | None,
    header_image: str | None = None,
    igdb_keys: tuple[str | None, str | None] = (None, None),
) -> list[AssetKind]:
    """Tries each source for each kind of art until one saves. Returns what was
    saved."""
    # the person's own key, else the one the server was set up with
    api_key = steamgriddb_api_key or settings.STEAMGRIDDB_API_KEY
    sources = _ArtSources(app_id, title, api_key, header_image, igdb_keys)
    saved: list[AssetKind] = []
    for kind in kinds:
        async for address in sources.urls(kind):
            if await download_asset(address, game_id, kind):
                saved.append(kind)
                break
    return saved


def _same_picture(saved: Path, image: bytes) -> bool:
    try:
        with Image.open(saved) as one, Image.open(BytesIO(image)) as other:
            a = one.convert("RGB").resize(_COMPARE_SIZE)
            b = other.convert("RGB").resize(_COMPARE_SIZE)
    except OSError:
        return False
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3 <= _SAME_PICTURE


async def replace_poor_cover(
    game: Any,
    app_id: int,
    title: str | None,
    steamgriddb_api_key: str | None,
    igdb_keys: tuple[str | None, str | None] = (None, None),
) -> bool:
    """Swaps a Steam game's cover for a real one, but only when the saved file is
    shown to be Steam's old small copy or its generated image, by comparing the
    pictures. Nothing records where a cover came from, so this is what keeps a
    cover someone chose out of it. Returns whether it was replaced."""
    if "key_art" in (game.locked_fields or []) or not game.folder_location:
        return False
    saved = (
        DATA_ROOT / str(game.user_id) / "games" / game.folder_location / ASSET_FILENAMES["key_art"]
    )
    if not saved.is_file():
        return False
    store, generated = await asyncio.to_thread(steam_store_art, app_id)
    if not store and not generated:
        return False  # Steam did not answer, so nothing is known about this cover
    poor = [address for address in (steam_cdn_art_urls(app_id)["key_art"], generated) if address]
    for address in poor:
        try:
            image = await asyncio.to_thread(download_image, address)
        except RemoteImageError:
            continue
        if _same_picture(saved, image):
            break
    else:
        return False
    api_key = steamgriddb_api_key or settings.STEAMGRIDDB_API_KEY
    sources = _ArtSources(app_id, title, api_key, None, igdb_keys)
    async for address in sources.urls("key_art"):
        if address not in poor and await download_asset(address, game.id, "key_art"):
            return True
    return False
