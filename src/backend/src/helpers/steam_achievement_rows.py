"""Pure builders for a Steam game's stored achievement rows."""


def needs_community_descriptions(schema: dict[str, dict]) -> bool:
    """Whether some hidden achievement has no description, which Steam's Web API
    leaves out for hidden ones: the community feed is only worth a request then."""
    return any(d.get("hidden") and not d.get("description") for d in schema.values())


def steam_achievement_rows(
    schema: dict[str, dict],
    unlocked: list[dict],
    percentages: dict[str, float] | None = None,
    descriptions: dict[str, str] | None = None,
) -> list[dict]:
    """Stored rows for one Steam game: its schema says what each achievement is
    (name, icons, whether Steam marks it hidden), the player list says which
    are unlocked and when, and the percentages (when fetched) how many players
    have it."""
    # Steam is not consistent about the case of an achievement's internal name
    # between the schema and the player's list (some games differ), so match
    # without regard to case or an unlocked achievement shows as locked
    player_by_name = {a["apiname"].lower(): a for a in unlocked if a.get("apiname")}

    def player(api_name: str) -> dict:
        return player_by_name.get(api_name.lower(), {})

    rows = [
        {
            "external_id": api_name,
            "name": defn.get("displayName") or api_name,
            # Steam leaves a hidden achievement's description out of the schema:
            # the player list has it once you've unlocked it, and the community
            # feed has it either way
            "description": defn.get("description")
            or player(api_name).get("description")
            or (descriptions or {}).get(api_name.lower())
            or (descriptions or {}).get(f"name:{(defn.get('displayName') or '').lower()}")
            or None,
            "icon_url": defn.get("icon")
            if player(api_name).get("achieved")
            else defn.get("icongray"),
            "unlocked": bool(player(api_name).get("achieved")),
            "unlocked_at": player(api_name).get("unlocktime") or None,
            "hidden": bool(defn.get("hidden")),
        }
        for api_name, defn in schema.items()
    ]
    if percentages is not None:
        for row in rows:
            row["global_percent"] = percentages.get(str(row["external_id"]))
    return rows
