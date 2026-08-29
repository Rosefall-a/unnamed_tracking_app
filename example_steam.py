"""
Steam Storefront API client.

The Steam Storefront API is unofficial/undocumented but widely used.
No API key is required. Docs (community-maintained):
https://wiki.teamfortress.com/wiki/User:RJackson/StorefrontAPI

Endpoints used here:
- App details:  https://store.steampowered.com/api/appdetails
- App list:     https://api.steampowered.com/ISteamApps/GetAppList/v2/
- Featured:     https://store.steampowered.com/api/featuredcategories
- Search:       https://store.steampowered.com/api/storesearch
"""

import time
import requests


BASE_URL = "https://store.steampowered.com/api"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; SteamDataFetcher/1.0)"})


def get_app_details(app_id: int, country: str = "us", currency: str = "USD") -> dict | None:
    """
    Fetch full details for a single app (game/DLC/etc) by its Steam AppID.
    Returns the 'data' dict on success, or None if the app has no store page.
    """
    params = {"appids": app_id, "cc": country, "l": "en"}
    resp = SESSION.get(f"{BASE_URL}/appdetails", params=params, timeout=10)
    resp.raise_for_status()
    payload = resp.json()

    app_data = payload.get(str(app_id))
    if not app_data or not app_data.get("success"):
        return None
    return app_data["data"]


def get_app_details_bulk(app_ids: list[int], delay: float = 1.0) -> dict[int, dict]:
    """
    Fetch details for multiple AppIDs one at a time (the endpoint only
    reliably supports a single appid per request). `delay` avoids
    rate-limiting/soft bans from Steam.
    """
    results = {}
    for app_id in app_ids:
        data = get_app_details(app_id)
        if data:
            results[app_id] = data
        time.sleep(delay)
    return results


def search_store(term: str, country: str = "us") -> list[dict]:
    """Search the Steam store by keyword."""
    params = {"term": term, "cc": country, "l": "en"}
    resp = SESSION.get(f"{BASE_URL}/storesearch", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("items", [])


def get_featured_categories(country: str = "us") -> dict:
    """Fetch the storefront's featured/specials/new-releases categories."""
    params = {"cc": country, "l": "en"}
    resp = SESSION.get(f"{BASE_URL}/featuredcategories", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_full_app_list() -> list[dict]:
    """
    Fetch every app on Steam (appid + name). This is a large payload
    (100k+ entries) from the separate ISteamApps endpoint.
    """
    url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
    resp = SESSION.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()["applist"]["apps"]


def print_app_details(details: dict) -> None:
    """Pretty-print the most useful fields from an appdetails response."""
    print("\n" + "=" * 60)
    print(f"{details.get('name')}  (AppID: {details.get('steam_appid')})")
    print("=" * 60)

    print(f"Type: {details.get('type')}")
    print(f"Release date: {details.get('release_date', {}).get('date')}")
    print(f"Required age: {details.get('required_age', 0)}")

    price = details.get("price_overview")
    if price:
        print(f"Price: {price['final_formatted']}", end="")
        if price.get("discount_percent"):
            print(f"  (-{price['discount_percent']}%, was {price['initial_formatted']})", end="")
        print()
    elif details.get("is_free"):
        print("Price: Free")

    devs = ", ".join(details.get("developers", []))
    pubs = ", ".join(details.get("publishers", []))
    print(f"Developer(s): {devs}")
    print(f"Publisher(s): {pubs}")

    genres = ", ".join(g["description"] for g in details.get("genres", []))
    categories = ", ".join(c["description"] for c in details.get("categories", []))
    print(f"Genres: {genres}")
    print(f"Categories: {categories}")

    plat = details.get("platforms", {})
    supported = [name for name, ok in plat.items() if ok]
    print(f"Platforms: {', '.join(supported)}")

    if details.get("metacritic"):
        print(f"Metacritic: {details['metacritic']['score']}")

    if details.get("recommendations"):
        print(f"Recommendations: {details['recommendations']['total']:,}")

    print(f"\nShort description:\n{details.get('short_description')}")

    print(f"\nHeader image: {details.get('header_image')}")
    print(f"Website: {details.get('website')}")

    screenshots = details.get("screenshots", [])
    if screenshots:
        print(f"\nScreenshots ({len(screenshots)} total), first one: {screenshots[0]['path_full']}")

    movies = details.get("movies", [])
    if movies:
        print(f"Trailers/movies: {len(movies)} available")


def interactive_search() -> None:
    """Search by name, show top 5 numbered results, let the user pick one for full details."""
    term = input("Search for a game: ").strip()
    if not term:
        print("No search term entered.")
        return

    results = search_store(term)[:5]
    if not results:
        print("No results found.")
        return

    print("\nTop results:")
    for i, item in enumerate(results, start=1):
        price = item.get("price")
        price_str = f"${price['final'] / 100:.2f}" if price else "Free/N/A"
        print(f"  {i}. {item['name']}  ({price_str})")

    choice = input("\nEnter a number for details (or press Enter to quit): ").strip()
    if not choice:
        return
    if not choice.isdigit() or not (1 <= int(choice) <= len(results)):
        print("Invalid choice.")
        return

    selected = results[int(choice) - 1]
    details = get_app_details(selected["id"])
    if details:
        print_app_details(details)
    else:
        print("Could not fetch details for that app (it may have no store page).")


if __name__ == "__main__":
    interactive_search()