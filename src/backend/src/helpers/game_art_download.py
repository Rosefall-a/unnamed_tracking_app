"""Downloading a game's artwork from a web address into its folder."""

import asyncio
import json
import re
from collections.abc import AsyncIterator, Iterable
from typing import Any
from uuid import UUID

import requests

from src.features.metadata.games.steam_grid_db import SteamGridDBClient, SteamGridDBError
from src.helpers.remote_images import RemoteImageError, download_image
from src.helpers.save_game_asset import ASSET_FILENAMES, DATA_ROOT, AssetKind, save_game_asset

_ART_KINDS: tuple[AssetKind, ...] = ("key_art", "banner", "logo", "icon")
_STORE_ITEMS_URL = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/"
_STORE_ASSET_HOST = "https://shared.akamai.steamstatic.com/store_item_assets/"
_COMMUNITY_ICON_HOST = "https://cdn.akamai.steamstatic.com/steamcommunity/public/images/apps"
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


def steam_store_art_urls(app_id: int) -> dict[AssetKind, str]:
    """Art of newer Steam games lives under a hashed path that the fixed names
    above cannot reach, so its real address comes from the store's own item
    list. Empty when Steam does not answer."""
    query = {
        "ids": [{"appid": app_id}],
        "context": {"language": "english", "country_code": "US"},
        "data_request": {"include_assets": True},
    }
    try:
        response = requests.get(_STORE_ITEMS_URL, params={"input_json": json.dumps(query)}, timeout=10)
        response.raise_for_status()
        items = response.json().get("response", {}).get("store_items") or []
    except (requests.RequestException, ValueError, AttributeError):
        return {}
    assets = (items[0].get("assets") or {}) if items else {}
    url_format = assets.get("asset_url_format")
    if not url_format:
        return {}

    def url(filename: str | None) -> str | None:
        return _STORE_ASSET_HOST + url_format.replace("${FILENAME}", filename) if filename else None

    found: dict[AssetKind, str | None] = {
        "key_art": url(assets.get("library_capsule_2x") or assets.get("library_capsule")),
        "banner": url(assets.get("library_hero_2x") or assets.get("library_hero")),
    }
    if assets.get("community_icon"):
        found["icon"] = f"{_COMMUNITY_ICON_HOST}/{app_id}/{assets['community_icon']}.jpg"
    return {kind: address for kind, address in found.items() if address}


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
        self, app_id: int | None, title: str | None, api_key: str | None, header_image: str | None
    ) -> None:
        self._app_id, self._title, self._api_key = app_id, title, api_key
        self._header_image = header_image
        self._store: dict[AssetKind, str] | None = None
        self._client: SteamGridDBClient | None = None
        self._sgdb_id: int | None = None
        self._sgdb_asked = False

    async def _store_url(self, kind: AssetKind) -> str | None:
        if self._store is None:
            self._store = await asyncio.to_thread(steam_store_art_urls, self._app_id)
        return self._store.get(kind)

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
                self._client.get_game_images, self._sgdb_id, _SGDB_IMAGE_TYPES[kind]
            )
        except Exception:  # best-effort: one odd answer must not fail a whole import
            return []
        return [image.url for image in images[:3] if image.url]

    async def urls(self, kind: AssetKind) -> AsyncIterator[str]:
        if self._app_id:
            fixed = steam_cdn_art_urls(self._app_id).get(kind)
            if fixed:
                yield fixed
            # Steam's own icon is 32 pixels: only used when nothing better exists
            if kind != "icon":
                address = await self._store_url(kind)
                if address:
                    yield address
        # a wide header would be cropped badly into the portrait cover, so it is
        # only ever a banner
        if kind == "banner" and self._header_image:
            yield self._header_image
        for address in await self._sgdb_urls(kind):
            yield address
        if kind == "icon" and self._app_id:
            address = await self._store_url(kind)
            if address:
                yield address


async def fill_art(
    game_id: UUID,
    kinds: Iterable[AssetKind],
    app_id: int | None,
    title: str | None,
    steamgriddb_api_key: str | None,
    header_image: str | None = None,
) -> list[AssetKind]:
    """Tries each source for each kind of art until one saves. Returns what was
    saved."""
    sources = _ArtSources(app_id, title, steamgriddb_api_key, header_image)
    saved: list[AssetKind] = []
    for kind in kinds:
        async for address in sources.urls(kind):
            if await download_asset(address, game_id, kind):
                saved.append(kind)
                break
    return saved
