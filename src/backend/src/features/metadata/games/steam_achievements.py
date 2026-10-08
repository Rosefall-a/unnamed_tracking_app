"""Reading one Steam game's achievements for a player, shared by the library
sync and the batched import step."""

import asyncio

from src.features.metadata.games import steam
from src.helpers.steam_achievement_rows import needs_community_descriptions

# the schema (what each achievement is), the player's list (None when Steam
# would not say what is unlocked) and community descriptions (or None)
SteamAchievementData = tuple[dict[str, dict], list[dict] | None, dict[str, str] | None]


async def fetch_steam_achievements(
    steam_id: str, api_key: str, app_id: int
) -> SteamAchievementData:
    """One game's achievement data. The community feed is only asked when a
    hidden achievement has no description. A failed request reads as a game
    without achievements, so one game cannot fail a whole import."""
    try:
        schema = await asyncio.to_thread(steam.get_schema_for_game, api_key, app_id)
        if not schema:
            # no achievements to ask about: skipping the player's list saves a
            # request for every such game (often a third of a library), and
            # fewer requests means fewer of Steam's "too many requests"
            return {}, [], None
        unlocked = await asyncio.to_thread(steam.get_player_achievements, steam_id, api_key, app_id)
    except steam.SteamLibraryError:
        return {}, [], None
    descriptions = None
    if needs_community_descriptions(schema):
        descriptions = await asyncio.to_thread(steam.get_community_descriptions, steam_id, app_id)
    return schema, unlocked, descriptions
