# Metadata providers

Unnamed Tracking App uses the existing game metadata-provider registry for both adding games and refreshing metadata on an existing game. Provider order and field-saving preferences are configured per user under **Settings → Metadata → Scan Settings / Metadata/API**.

## Repull metadata from the game editor

Open **Edit Game → Media → Repull Metadata**. The editor first performs a provider lookup and shows a confirmation describing the fields that would change and any locked fields that will be preserved.

The refresh uses the current game title and requires an exact title match (ignoring case and common trademark/copyright marks). A fuzzy or missing match is not applied.

The workflow is:

1. Choose whether missing cover/banner artwork may be added.
2. Click **Repull Metadata**.
3. Review the provider and the fields that would change.
4. Cancel, or confirm **Apply refresh**.
5. The editor reloads the saved game data after a successful refresh.

Existing artwork is never replaced by this editor action. Replacing artwork remains a separate explicit action.

## Manual fields and locked metadata

When a user manually changes a metadata field through the game editor, that field is recorded as a manual override (`locked_fields`). Future provider refreshes skip it. This protects intentional values such as a custom description, developer/publisher correction, tags, release date, or other supported metadata.

Ratings, playtime, ownership information, notes, status, and other personal library state are not part of the provider refresh and are left unchanged.

If a provider does not return a value, the existing value is not cleared.

## Provider selection and priority

The refresh calls the same configured provider registry used by metadata search. The user's provider order determines which data provider is consulted first; image providers remain separate from data providers. Provider failures are reported without discarding successful results from other providers.

Provider credentials and field-save toggles continue to be managed in the existing metadata settings. No second provider configuration is introduced for the game editor.

## Provider failures and stale previews

A provider outage, rate limit, malformed result, or no-match result does not modify the game. If the game changes after the preview but before applying it, the backend rejects the stale apply with a conflict and the editor asks the user to refresh/retry. This prevents a metadata refresh from overwriting a newer edit made in another tab or session.

Metadata changes are recorded in the existing game metadata history, so provider-applied field changes remain visible in the game's **History** tab.

## Developer notes

The editor uses `/api/game/{game_id}/metadata/refresh`, which calls `features.metadata.games.search.search_game_metadata` with the requesting user's existing provider preferences and credentials. The endpoint owns authorization, exact-match validation, manual-field protection, history updates, artwork handling, and stale-preview checks; clients do not send arbitrary provider data to the game update API.
Games are searched on Steam, GOG, IGDB, GiantBomb, RetroAchievements and
HowLongToBeat; SteamGridDB and ScreenScraper add artwork. Movies and TV use
TMDB, OMDb and TVmaze, anime uses AniList. Cover and banner artwork can also be
uploaded by hand.

## Where keys go

Keys can be set in two places:

| Place | Who | Used for |
| --- | --- | --- |
| Settings › Metadata/API | Every user, for themselves | That user's searches and library syncs. |
| Settings › Server Integrations | Administrators | Everyone who hasn't saved their own key. |

A user's own key always wins for that user. The server-wide key is the
fallback; a Server Integrations field that is set in `.env` is locked to the
`.env` value. On Settings › Metadata/API, a provider that
works through the server's key shows **Using server key** rather than **Not
configured**, so the same provider appearing in both places isn't a sign
that they're out of sync.

IGDB, TMDB, OMDb and TVDB are server-wide only.
## Safe operation

- Keep provider client secrets and API keys out of browser storage, screenshots, logs, and the wiki.
- Environment-managed server credentials should be rotated through deployment tooling.
- Search results are previews; users review data before creating a record.
- Refresh operations respect supported locked fields and user ownership.
- Provider failures are contained and reported rather than granting a fallback access path.

Plugins do not receive provider credentials. A plugin can use only the normalized methods granted through Plugin API v1.


## Steam tags as genres

Steam's own genres are broad: Elden Ring is only Action and RPG. Steam players
also vote on tags, and those describe a game far better. For Elden Ring the
most voted are Souls-like, Open World, Dark Fantasy, RPG, Difficult and Action
RPG.

With **Use popular Steam tags as genres** on (it is on by default), a Steam
game's genres become its most voted tags plus its official genres, so Elden
Ring gets Souls-like, Open World, Dark Fantasy, RPG, Difficult, Action RPG and
so on. Tags that are not genres are left out: how many play it (Singleplayer,
Multiplayer, Co-op, PvP), how it is controlled (Controller support, VR), what
Steam adds around it (Steam Achievements, Early Access, Free to Play),
opinions (Great Soundtrack, Replay Value), and content labels (Violent, Family
Friendly). At most 12 player tags are kept. A game that players have barely
tagged keeps its official genres only.

The setting is under Settings, Metadata, Scan & providers. It applies:

- when a Steam game is added by a library sync;
- when a game's metadata is searched or refreshed. Because other providers such
  as IGDB can fill the genres first, the Steam tags replace them when the search
  matched a Steam game;
- when you press **Update my Steam games now**, which re-reads the tags of the
  Steam games already in the library. It works through them a few at a time and
  reads one store page a second, so a large library takes a few minutes. Tags you
  added yourself are kept.

The tags are read from each game's public Steam store page, the only place Steam
shows them. If a page cannot be read, the game keeps the tags it has. With the
setting off, Steam games get Steam's official genres as before.
