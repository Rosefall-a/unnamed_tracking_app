from __future__ import annotations

from datetime import datetime
from typing import Any

from src.core.config import settings
from src.features.metadata.games import steam
from src.features.metadata.games.steam_grid_db import SteamGridDBClient, SteamGridDBError


def _parse_release_date(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    for date_format in ("%d %b, %Y", "%b %d, %Y", "%Y"):
        try:
            return datetime.strptime(value.strip(), date_format).date().isoformat()
        except ValueError:
            continue
    return None


def _steam_result(item: dict[str, Any], details: dict[str, Any] | None) -> dict[str, Any]:
    details = details or {}
    app_id = int(str(item.get("id") or details.get("steam_appid")))
    title = details.get("name") or item.get("name") or ""
    genres = [entry["description"] for entry in details.get("genres", []) if entry.get("description")]
    features = [entry["description"] for entry in details.get("categories", []) if entry.get("description")]
    required_age = details.get("required_age")
    return {
        "provider": "Steam",
        "provider_id": str(app_id),
        "title": title,
        "description": details.get("short_description") or None,
        "release_date": _parse_release_date(details.get("release_date", {}).get("date")),
        "developer": ", ".join(details.get("developers", [])) or None,
        "publisher": ", ".join(details.get("publishers", [])) or None,
        "age_rating": f"{required_age}+" if required_age else None,
        "tags": genres,
        "features": features,
        "links": [{"label": "Steam Store", "url": f"https://store.steampowered.com/app/{app_id}/"}],
        "key_art_url": details.get("header_image") or item.get("tiny_image"),
        "key_art_urls": [],
        "banner_url": details.get("background_raw") or details.get("header_image"),
        "banner_urls": [],
        "logo_url": None,
        "logo_urls": [],
        "icon_url": None,
        "icon_urls": [],
    }


def _add_steamgriddb_art(result: dict[str, Any], client: SteamGridDBClient) -> str:
    try:
        match = client.get_game_by_name(result["title"])
        if not match:
            return ""
        game_id = match.get("id") or match.get("game_id")
        if game_id is None:
            return "SteamGridDB returned a match without a game ID."
        result["links"].append({
            "label": "SteamGridDB",
            "url": f"https://www.steamgriddb.com/game/{game_id}",
        })
        image_fields = {
            "grids": ("key_art_urls", "key_art_url"),
            "heroes": ("banner_urls", "banner_url"),
            "logos": ("logo_urls", "logo_url"),
            "icons": ("icon_urls", "icon_url"),
        }
        for image_type, (list_field, default_field) in image_fields.items():
            images = client.get_game_images(game_id, image_type=image_type, limit=10)
            urls = [image.url for image in images if image.url][:10]
            result[list_field] = urls
            if urls:
                result[default_field] = urls[0]
        return ""
    except (SteamGridDBError, TypeError, ValueError) as exc:
        return str(exc)


def search_game_metadata(query: str, limit: int = 8) -> dict[str, Any]:
    """Search configured providers and return normalized creation-form data."""
    results: list[dict[str, Any]] = []
    provider_errors: list[str] = []
    for item in steam.search_store(query)[:limit]:
        app_id = item.get("id")
        if app_id is None:
            continue
        details = steam.get_app_details(int(app_id)) if app_id else None
        if details and details.get("type") not in (None, "game"):
            continue
        results.append(_steam_result(item, details))

    if settings.STEAMGRIDDB_API_KEY:
        try:
            client = SteamGridDBClient()
            for result in results:
                provider_error = _add_steamgriddb_art(result, client)
                if provider_error:
                    provider_errors.append(provider_error)
        except SteamGridDBError as exc:
            provider_errors.append(str(exc))

    return {
        "query": query,
        "providers": ["Steam"] + (["SteamGridDB"] if settings.STEAMGRIDDB_API_KEY else []),
        "provider_errors": provider_errors,
        "results": results,
    }