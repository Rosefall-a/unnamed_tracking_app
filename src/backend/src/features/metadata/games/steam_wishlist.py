"""A player's Steam wishlist: the app ids they have wishlisted."""

import requests

from src.features.metadata.games.steam import _WEB_API_BASE, SESSION, SteamLibraryError


def get_wishlist_app_ids(steam_id: str, api_key: str) -> list[int]:
    """The wishlisted app ids, most wanted first. An empty or hidden wishlist is
    just an empty list; only being unable to reach Steam is an error."""
    try:
        resp = SESSION.get(
            f"{_WEB_API_BASE}/IWishlistService/GetWishlist/v1/",
            params={"key": api_key, "steamid": steam_id},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise SteamLibraryError(f"Could not reach Steam: {exc}") from exc
    if resp.status_code >= 400:
        return []
    try:
        items = resp.json().get("response", {}).get("items", [])
    except ValueError:
        return []
    ranked = sorted(items, key=lambda i: i.get("priority") or 0)
    return [int(i["appid"]) for i in ranked if str(i.get("appid", "")).isdigit()]
