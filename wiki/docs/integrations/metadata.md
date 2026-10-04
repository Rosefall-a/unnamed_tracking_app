# Metadata Providers

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
