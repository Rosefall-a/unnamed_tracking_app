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
