# Metadata providers

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
