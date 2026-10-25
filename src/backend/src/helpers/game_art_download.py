"""Downloading a game's artwork from a web address into its folder."""

import asyncio
from uuid import UUID

from src.features.metadata.games.steam_grid_db import SteamGridDBClient
from src.helpers.remote_images import RemoteImageError, download_image
from src.helpers.save_game_asset import AssetKind, save_game_asset


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


async def steamgriddb_key_art_url(app_id: int, api_key: str | None) -> str | None:
    """SteamGridDB's "grids" are the portrait (~2:3) shape key_art actually
    needs. Steam's storefront API has no portrait art at all (header and
    capsule images are all wide), so using one of those as a key_art
    fallback (an earlier version of this function did, briefly) just
    force-crops a landscape image into a portrait slot and produces a
    mangled cover. Looked up by Steam appid, like the Steam import, so there
    is no title-matching ambiguity. Does nothing without a key."""
    if not api_key:
        return None
    try:
        client = SteamGridDBClient(api_key)
        sgdb_game = await asyncio.to_thread(client.get_game_by_steam_appid, app_id)
        if not sgdb_game or not sgdb_game.get("id"):
            return None
        images = await asyncio.to_thread(client.get_game_images, sgdb_game["id"], "grids")
    except Exception:
        return None
    return images[0].url if images else None
