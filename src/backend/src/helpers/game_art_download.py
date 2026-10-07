"""Downloading a game's artwork from a web address into its folder."""

import asyncio
from uuid import UUID

import requests

from src.core.config import settings as app_settings
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
        response = await asyncio.to_thread(requests.get, url, timeout=20)
        response.raise_for_status()
    except requests.RequestException:
        return False
    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if not content_type.startswith("image/"):
        return False
    if len(response.content) > app_settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        return False
    try:
        await save_game_asset(response.content, game_id, asset_kind)
        return True
    except (OSError, ValueError):
        return False
