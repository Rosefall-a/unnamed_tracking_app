# Bugfix log (branch: bugfixes)

Running notes for the PR description. Each entry: why it broke, how it was fixed.
Do not commit this file.

## Done

### New profile picture only showed in Settings
Why: only the Settings page rendered the uploaded picture. The sidebar and the
top-bar profile menu (`ProfileMenu.vue`) always drew the user's initials, and
the cache-busting stamp lived inside the Settings component, so nothing else
knew an upload had happened.
Fix: a shared `avatarVersion` in `state/auth.ts` is bumped after an upload.
`ProfileMenu.vue` (used by the sidebar and the account chip) now shows the
picture, refetches when the version changes, and falls back to initials when
the user has no picture.

### Uploading a HEIC picture failed with "File must be a valid image"
Why: Pillow cannot read HEIC/HEIF, and the upload route reported that as a
generic invalid image. The frontend also replaced the server message with a raw
status line.
Fix: the upload route detects HEIC/HEIF by its `ftyp` brand and returns a 415
with "HEIC pictures are not supported. Save it as a JPEG or PNG and try again."
The frontend now shows the server's message as is.

### Plan to Watch (any status tab) reset to All on refresh
Why: the active status tab was a plain in-memory ref in `MediaLibraryView.vue`,
so a refresh always started on All.
Fix: the tab is stored in `sessionStorage` per library and restored on load
(and re-sent to the server query). It is cleared when the library component
unmounts, so leaving the page and coming back starts on All, while a refresh
keeps the tab.

### Account connections showed "0 games" for accounts that were never connected
Why: the provider-credentials endpoint returns a `library_games` count of 0 for
every library-sync provider, and `ConnectionsSection.vue` printed it whether or
not the account was connected. Xbox has no count, so it said "Not connected"
while PlayStation and RetroAchievements said "0 games". The pill said "Not set
up" and the detail text was lowercase ("games", "synced ...").
Fix: detail text (name, game count, last sync) is built only for connected
accounts. Everything else reads "Not connected" (the pill too). Wording is
capitalised: "Games", "Synced 2h ago", "Never synced".

### Media top bar switcher had no icons, and Collections used a different icon
Why: `MediaKindSwitch.vue` defined its options without `icon`, while the Games
bar (`GameTopBar.vue`) gives each option one.
Fix: Movies, TV Shows and Anime use the sidebar's own icons, and Collections
uses the exact icon from the Games bar.

### Duplicate tag filter pills in the Games library
Why: the Genre dropdown (`genreFilter`) and the "Tags (any of)" chips
(`tagsFilter`) pick from the same list, and links such as `?tag=` set the
dropdown. Choosing the same value in both showed two identical pills for what
is one filter.
Fix: the tag pill is skipped when it equals the selected genre. Not done: the
URL does not yet mirror every filter, so filtered searches are still not
shareable links (needs a decision on the URL format).

### Scrolling far in a large Movie/TV/Anime library blanked the list and jumped to the top
Why: `MediaLibraryView.vue` rendered `<p v-if="loading">Loading...</p>` ahead of
the list in the same `v-if` chain. Loading the next page sets `loading`, so the
whole list was unmounted and rebuilt, which resets the scroll position. The
"Loading more..." footer was inside the hidden list.
Fix: the full-page "Loading..." only shows when nothing is loaded yet
(`loading && !items.length`), so loading more pages keeps the list in place.

### Sidebar Media > Collections still used the old list icon
Why: the earlier icon change covered only the top bar switcher; `SidebarNav.vue`
had its own copy of the icon.
Fix: the sidebar entry now uses the same stacked-layers icon as Games Collections.

### Steam achievements all showed as locked for some accounts (Skyrim)
Why: the unlocked list is matched to the schema by the achievement's internal
name, with an exact-case comparison, and `get_player_achievements` turned every
failure (private game details, 4xx, `success: false`) into an empty list, which
reads as "nothing unlocked". Either one produces 0 of 50 with no message.
Not confirmed against the affected account (no access to it): these are the two
ways the code can produce that symptom.
Fix: names are matched case-insensitively (`helpers/steam_achievement_rows.py`),
and the single-game refresh now raises a clear message when Steam says the
account's game details are private ("set Profile > Privacy Settings > Game
details to Public, then refresh"). The bulk library sync keeps its old
behaviour so one private game cannot fail the whole sync.
Follow-up: the affected account has its Steam ID and API key saved and still
showed nothing. Steam's Web API may withhold achievement data from a private
profile even for the key's own owner (reports online say so; not verified
here). The single-game refresh now also fails with an explicit message when
Steam returns no player data at all for a game that has achievements. Steam
lists locked achievements too, so an empty answer means no data, not zero
unlocked. The message names the app id, the number of achievements in the
game, and the three things to check (Game details public, key and Steam ID
from one account, correct edition).

### Yamtrack import created duplicates because Yamtrack and AniList spell titles differently
Why: Yamtrack stores the Japanese title and the AniList/MAL imports store the
English one. Existing-show detection compared source plus id, then an exact
title and date, so the same show never matched and was imported twice. This is
also why anime was switched off in #422.
Fix: anime rows are matched first by provider id (MAL id against `external_id`,
AniList id against `anilist_id`, regardless of which importer created the
show), then by title against every spelling the show has (`title`,
`title_english`, `title_romaji`, `title_native`). Anime import is turned back
on, and the "anime is not imported" notes in the UI are removed.
Tests: `test_yamtrack_import.py` (parse, anime included) and
`test_yamtrack_anime_match.py` (id match, alternate title match, no false match).

### Artwork was only saved locally after someone first viewed it
Why: movie, TV and anime posters/backdrops were copied to the server the first
time a page asked for them (so the first view still waited on TMDB/AniList),
achievement and trophy icons were always loaded straight from Steam,
PlayStation and RetroAchievements, and notification posters used whatever
address was stored with the notification.
Fix: `helpers/image_prefetch.py` listens for rows being saved (a new or edited
movie/TV show/anime, a metadata refresh, an import, a new achievement) and
downloads the poster, backdrop (or the poster as hero) and icon in the
background (4 big images at a time, 16 icons at a time), into the same cache the image routes serve.
Pictures that fail are left to the route, which still redirects to the
original. Achievement icons are served from `/api/achievement-icon/{id}` and
kept once per address under `/data/cache/achievement-icons`. Notifications now
always use the show's own poster, served from the local copy (a "new season
listed" notice used to use the sequel's poster). A title with a backdrop uses
one file for backdrop and hero instead of two. Existing titles are still copied
on first view; nothing backfills them automatically.
Seasons keep their own season posters, as before.

### Game notes flashed a loading skeleton before appearing
Why: the notes tab drew its three placeholder cards the instant it opened, so a
load that finished in a few milliseconds still showed them for one frame.
Fix: `utils/useSlowFlag.ts` only turns the skeleton on after the wait has lasted
300 ms. Anything faster shows no skeleton at all. Reusable for other loaders.

### Steam import: wishlist, and an import that errored with a 500 after saving everything
Why (500): the whole import ran inside one request: save every game and
achievement, then for each new game read its store page, tags, series and
three artwork files (about a second per game, throttled), with a single commit
at the end and `gather()` aborting on the first exception. A big library ran
past the proxy/browser timeout, or one game's failure aborted the batch, and
the request returned a 500 after the games had been saved but before the
enrichment, which is where the images come from. This is inferred from the
code, not reproduced against that user's account.
Fix: the sync route now only saves games and achievements and returns the new
game ids. `api/routes/steam_import_steps.py` enriches them in batches of 5
(`POST /api/library-sync/steam/enrich`), committing after each game and
counting a failed game instead of aborting. `services/librarySync.ts` runs the
batches after the sync, so callers are unchanged.
Wishlist: new preference `steam_import_wishlist` (off by default) with a toggle
under Settings > Metadata > Scan & providers. When on, the import also reads the
wishlist (`IWishlistService/GetWishlist`) and adds each game as Wishlist under a
placeholder name that enrichment replaces with the store's name. A wishlisted
game is never flagged stale, and one you later buy gets a normal status on the
next import. Needs the account's game details to be public; a hidden wishlist
imports nothing.

## To do

