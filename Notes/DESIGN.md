# Archive — Design Document

*The complete specification. Everything in this document is in scope; nothing outside it is.*

> **Product name:** `Archive` is a placeholder throughout. The final name lives in one
> constant (`lib/constants.ts → APP_NAME`) so renaming is a one-line change.

---

## Contents

1. [What we're building](#1-what-were-building)
2. [Principles](#2-principles)
3. [Scope](#3-scope)
4. [Stack](#4-stack)
5. [Repository layout](#5-repository-layout)
6. [Database schema](#6-database-schema)
7. [Metadata system](#7-metadata-system)
8. [File storage system](#8-file-storage-system)
9. [API surface](#9-api-surface)
10. [UI specification](#10-ui-specification)
11. [How it all connects](#11-how-it-all-connects)
12. [Build order](#12-build-order)
13. [Deployment](#13-deployment)
14. [Conventions](#14-conventions)

---

# 1. What we're building

A self-hosted web app that runs on a home server and keeps a permanent personal record of
games played and media watched.

Two halves:

**The tracker.** Games, movies, TV and anime in one catalogue. Metadata and artwork pulled
from IGDB, TMDB and AniList. Status, five-axis ratings, notes, tags, episode progress,
playtime. Comparable to MyAnimeList or Playnite, but yours.

**The archive.** Screenshots, clips, saves and documents attached to those items — or to
nothing at all. Bulk import, albums, thumbnails, a timeline of everything you've ever done.
This half is the reason to build it rather than use something else.

On top of both: achievements synced from Steam and RetroAchievements, a collectible card per
100%-completed game, optional prestige challenges, and a backlog with bounties.

Single user. Runs in Docker. Reachable over LAN and Tailscale. Works fully offline once data
is local.

---

# 2. Principles

**1. Local data is the source of truth.** Providers supply metadata, artwork and IDs. They
never own your ratings, notes, screenshots, history or cards. A sync never overwrites
something you typed.

**2. Everything important is replaceable.** Frontend, provider, drive, container, server —
any can be swapped without losing the archive.

**3. One application, clean modules.** A modular monolith. No microservices.

**4. A thing doesn't need metadata to be archived.** A screenshot with a title, a date and a
file is a valid record. Organising it later is optional.

**5. The filesystem alone can rebuild the archive.** Every asset gets a JSON sidecar. If
Postgres is destroyed and the backup fails, the drive is still walkable.

---

# 3. Scope

### Catalogue
Unified item model for games, movies, TV and anime · library grid with filter/sort/search ·
detail pages · full manual editing of every field · five artwork slots · status with history ·
five-axis ratings with confidence and history · personal rank · notes · tags and genres ·
favourites · resume notes · franchises and item relationships · custom fields

### Metadata
Pluggable provider interface · IGDB (games) · TMDB (movies, TV) · AniList (anime) ·
Steam library import · search → preview → import flow · local artwork storage · per-field
origin tracking · safe refresh that never clobbers edits · permanent response cache ·
offline handling

### Per-type
Movies: watched, watch date, rewatch history · TV/anime: seasons, episodes, per-episode
progress, continue watching · Games: platform versions, playtime, sessions, physical
ownership

### Archive
Content-addressed storage with hashing and sidecars · uploads with validation · three
thumbnail sizes · gallery with lightbox · Quick Capture · Inbox · contextual upload ·
create-item-from-asset · bulk importer with manual grouping · exact duplicate detection ·
clips with FFmpeg metadata · saves · documents · **albums** (named folders of assets inside
an item)

### Views
Home · backlog with priority · what should I play · timeline · calendar · on this day ·
manual collections · smart collections · global search · statistics · year in review ·
memories

### Achievements & cards
Achievement sets (core, subset and DLC all count) · Steam sync · RetroAchievements sync
including subsets · achievements UI · one card per 100%-completed game · card design with
flip · cards gallery · card sets · prestige challenges with uploaded proof

### Backlog
Bounties — a light nudge to return to a dropped game

### Operations
CI · Docker production build · Tailscale deployment · nightly backups with restore test ·
nightly maintenance jobs · data health page · mobile pass · performance pass · security pass ·
tests · appearance settings · grid/list toggle · command palette · background job queue ·
yearly packing · export bundle

**Approximately 1,100 team-hours.**

---

# 4. Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | TypeScript | Shared types across frontend and backend |
| Framework | Next.js (App Router) | UI and API in one deployable |
| Database | PostgreSQL 18 | Relational core, JSONB where useful, full-text search built in |
| ORM | Drizzle | SQL-shaped, real migration files, strong types |
| Validation | Zod | One schema validates form, API and database boundary |
| Styling | Tailwind + design tokens | |
| Components | shadcn/ui | Copy-paste components we own outright |
| Images | Sharp | Thumbnails and format conversion |
| Video | FFmpeg / ffprobe | Duration, resolution, poster frames |
| Jobs | pg-boss | Durable queue inside Postgres, no Redis |
| Auth | Maintained auth library, credentials provider | Never hand-rolled |
| Tests | Vitest, Playwright, Testcontainers | |
| Containers | Docker + Compose | |
| CI | GitHub Actions → GHCR | |

One application. No monorepo.

---

# 5. Repository layout

```
archive/
├── .github/workflows/
│   ├── ci.yml                    lint · typecheck · test · build
│   └── docker.yml                build image, push to GHCR on tag
│
├── app/                          Next.js App Router
│   ├── (auth)/login/
│   ├── (app)/
│   │   ├── layout.tsx            shell: sidebar, header, command palette
│   │   ├── page.tsx              home
│   │   ├── games/
│   │   │   ├── page.tsx          library
│   │   │   └── [id]/
│   │   │       ├── page.tsx      detail
│   │   │       └── edit/page.tsx
│   │   ├── movies/               ── same three files
│   │   ├── tv/                   ── same
│   │   ├── anime/                ── same
│   │   ├── backlog/
│   │   ├── achievements/
│   │   ├── cards/
│   │   │   ├── page.tsx          gallery
│   │   │   └── sets/[id]/
│   │   ├── archive/
│   │   │   ├── screenshots/
│   │   │   ├── clips/
│   │   │   ├── saves/
│   │   │   ├── documents/
│   │   │   └── inbox/
│   │   ├── import/               bulk importer
│   │   ├── timeline/             ?view=list|calendar
│   │   ├── memories/
│   │   ├── collections/[id]/
│   │   ├── search/
│   │   ├── stats/
│   │   │   └── year/[year]/
│   │   └── settings/
│   │       ├── appearance/
│   │       ├── providers/
│   │       ├── storage/
│   │       └── health/
│   └── api/                      see §9
│
├── components/
│   ├── ui/                       shadcn primitives
│   ├── media-card.tsx
│   ├── library-grid.tsx          the list engine's view layer
│   ├── filter-bar.tsx
│   ├── detail-shell.tsx
│   ├── entity-form.tsx           schema-driven edit form
│   ├── rating-widget.tsx
│   ├── asset-grid.tsx
│   ├── lightbox.tsx
│   ├── card-object.tsx           the collectible card, front/back/flip
│   ├── empty-state.tsx
│   ├── skeletons.tsx
│   └── command-palette.tsx
│
├── features/                     domain logic; no cross-imports between siblings
│   ├── catalogue/                media items, list engine, filters
│   ├── metadata/                 provider framework + field origin
│   │   └── providers/
│   │       ├── base.ts           MetadataProvider interface
│   │       ├── igdb.ts
│   │       ├── tmdb.ts
│   │       ├── anilist.ts
│   │       └── steam.ts
│   ├── assets/                   storage, hashing, thumbnails, sidecars
│   ├── import/                   bulk importer
│   ├── achievements/
│   ├── cards/
│   ├── prestige/
│   ├── timeline/
│   ├── memories/
│   ├── collections/
│   ├── search/
│   ├── stats/
│   ├── bounties/
│   └── maintenance/
│
├── db/
│   ├── schema.ts                 all tables
│   ├── index.ts                  client
│   ├── seed.ts
│   └── migrations/               generated, committed
│
├── lib/
│   ├── constants.ts              APP_NAME, enums
│   ├── zod/                      shared schemas
│   ├── auth.ts
│   ├── jobs.ts                   pg-boss setup + handlers
│   └── utils.ts
│
├── scripts/
│   ├── backup.ts
│   ├── restore-test.ts
│   ├── export.ts
│   └── pack-year.ts
│
├── docs/
│   ├── DESIGN.md                 this file
│   ├── glossary.md
│   ├── rating-rubric.md
│   └── decisions/                0001-name.md, 0002-postgres.md, …
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── Dockerfile
├── compose.yaml                  production
├── compose.dev.yaml              development
├── .env.example
└── README.md
```

---

# 6. Database schema

Every table has `id uuid primary key default gen_random_uuid()`, `created_at`, `updated_at`.
Personal tables carry `user_id` (single user today; keeps the door open).
Deletion is immediate after a confirm dialog — there is no trash.

## 6.1 Core catalogue

```sql
users
  id · username · password_hash · created_at

media_items                        -- games, movies, TV, anime all live here
  id
  type                             enum: game | movie | tv | anime
  title
  sort_title                       "Legend of Zelda, The"
  alt_titles                       jsonb array
  description
  release_date                     date
  runtime_minutes                  int, nullable        (movies)
  status                           enum: wishlist | backlog | playing | watching
                                       | paused | completed | mastered | dropped
  priority                         enum: low | normal | high, nullable
  favorite                         bool
  personal_rank                    int, nullable
  rating_story                     numeric(3,1), nullable
  rating_gameplay                  numeric(3,1), nullable
  rating_soundtrack                numeric(3,1), nullable
  rating_presentation              numeric(3,1), nullable
  rating_enjoyment                 numeric(3,1), nullable
  rating_overall                   numeric(3,2), generated
  rating_confidence                enum: low | medium | high, nullable
  notes                            text (markdown)
  resume_note                      text, nullable
  search_vector                    tsvector, generated
  created_at · updated_at

  indexes: (type, status) · (type, sort_title) · (favorite)
           GIN(search_vector) · GIN(title gin_trgm_ops)
```

Which rating axes are shown per type is UI config, not schema:
games use all five, movies and TV use story / soundtrack / presentation / enjoyment.

```sql
external_ids
  media_item_id → media_items
  provider                         enum: igdb | tmdb | anilist | steam
                                       | retroachievements
  external_id                      text
  url                              text, nullable
  unique(media_item_id, provider)

field_origins                      -- the anti-clobber table, see §7.3
  media_item_id → media_items
  field_name                       text        'description', 'cover', …
  source                           enum: provider | custom
  provider                         enum, nullable
  updated_at
  unique(media_item_id, field_name)

artwork
  media_item_id → media_items
  kind                             enum: cover | background | logo | icon | banner
  file_hash · path · width · height · bytes
  source                           enum: provider | custom
  unique(media_item_id, kind)

genres           id · name · slug
tags             id · name · slug
media_item_genres    (media_item_id, genre_id)
media_item_tags      (media_item_id, tag_id)

franchises       id · name · slug
media_item_franchises (media_item_id, franchise_id)

item_relations
  from_item_id → media_items
  to_item_id   → media_items
  kind         enum: sequel_of | prequel_of | remake_of | port_of
                   | spin_off_of | adapted_from | adaptation_of

custom_fields
  media_item_id → media_items
  name · type (text|number|boolean|date) · value text
```

## 6.2 Games

```sql
game_platforms                     -- one game, several platforms
  media_item_id → media_items
  platform                         text   'Steam', 'PlayStation 5', 'SNES'
  playtime_minutes                 int default 0
  status                           enum (same as media_items), nullable
  completion_percent               numeric(5,2), nullable
  owned_format                     enum: digital | physical | both | none, nullable
  purchase_date                    date, nullable
  purchase_price                   numeric(10,2), nullable
  condition                        text, nullable
  notes                            text, nullable

sessions
  user_id · media_item_id · game_platform_id (nullable)
  started_at · ended_at · duration_minutes · note
  index: (media_item_id, started_at desc)
```

## 6.3 Episodic media

```sql
seasons
  media_item_id → media_items
  number · title · episode_count · air_date
  unique(media_item_id, number)

episodes
  season_id → seasons
  number · title · air_date · runtime_minutes · description
  unique(season_id, number)

episode_watches                    -- one row per viewing, rewatches included
  user_id · episode_id · watched_at
  index: (user_id, watched_at desc)

watches                            -- movies and whole-item viewings
  user_id · media_item_id · watched_at · note
```

## 6.4 History

```sql
status_history
  media_item_id · from_status · to_status · changed_at

rating_history
  media_item_id · axis · old_value · new_value · changed_at
```

## 6.5 Archive assets

```sql
albums                             -- named folders of assets inside one item
  media_item_id → media_items
  name · description · sort_order
  unique(media_item_id, name)

assets
  user_id
  kind                             enum: screenshot | clip | save | document
  media_item_id                    → media_items, NULLABLE
  game_platform_id                 → game_platforms, nullable
  album_id                         → albums, nullable
  title                            text, nullable
  file_hash                        text unique        SHA-256
  path                             text               relative to STORAGE_PATH
  original_filename                text
  mime_type · bytes
  width · height                   int, nullable      images/video
  duration_seconds                 numeric, nullable  clips
  capture_date                     timestamptz        from EXIF/ffprobe/mtime
  clip_type                        enum: gameplay | achievement | highlight
                                       | funny | other, nullable
  source                           enum: manual | medal | imported | other
  save_type · restore_notes        text, nullable     saves
  achievement_id                   → achievements, nullable
  note                             text, nullable
  index: (media_item_id, capture_date desc) · (kind, capture_date desc)
         (album_id) · WHERE media_item_id IS NULL  -- the Inbox

asset_tags     (asset_id, tag_id)
```

## 6.6 Achievements and cards

```sql
achievement_sets                   -- a game has many: core, subsets, DLC
  media_item_id → media_items
  game_platform_id → game_platforms, nullable
  source                           enum: steam | retroachievements | manual
  external_id · parent_external_id  text, nullable
  name
  kind                             enum: core | subset | dlc
  achievement_count                int

achievements
  achievement_set_id → achievement_sets
  external_id · name · description · icon_path
  points                           int, nullable      RA
  global_percent                   numeric, nullable  rarity

achievement_unlocks
  user_id · achievement_id
  unlocked_at · hardcore bool
  unique(user_id, achievement_id)

cards                              -- exactly one per fully-completed game
  media_item_id → media_items      unique
  number                           serial, display number
  minted_at
  platform                         text     where it was earned
  achievement_count · completion_time_minutes · playtime_minutes
  personal_score · personal_rank
  unique(media_item_id)

card_sets            id · name · description · artwork_path
card_set_members     (card_set_id, media_item_id)   -- sets count games

prestige_challenges
  media_item_id → media_items
  type                             text     'nuzlocke', 'no_hit', 'speedrun', …
  name · description
  status                           enum: active | completed | abandoned
  started_at · completed_at · note

prestige_evidence
  prestige_challenge_id → prestige_challenges
  asset_id → assets
  note
```

**Completion rule:** a card is minted when every achievement across **all** of a game's
sets — core, subsets and DLC — is unlocked. One card per game, no tiers or variants.

## 6.7 Activity, collections, bounties

```sql
timeline_events
  user_id
  type          enum: item_added | status_changed | rating_changed
                    | asset_added | episode_watched | movie_watched
                    | achievement_unlocked | card_minted | prestige_completed
                    | session_logged | bounty_completed
  media_item_id · asset_id         nullable
  ref_table · ref_id               nullable, points at the source row
  occurred_at                      timestamptz
  metadata                         jsonb
  index: (user_id, occurred_at desc) · (media_item_id, occurred_at desc)

memories
  user_id · title · note · occurred_on
memory_items                       -- references, never copies
  memory_id · ref_type · ref_id

collections
  user_id · name · description
  kind                             enum: manual | smart
  filter                           jsonb, smart only
collection_items  (collection_id, media_item_id)

bounties
  user_id · media_item_id
  title · description
  status                           enum: active | completed | abandoned
  created_at · completed_at
```

## 6.8 System

```sql
provider_cache
  provider · endpoint · params_hash
  response jsonb · fetched_at
  unique(provider, endpoint, params_hash)

settings
  user_id · key · value jsonb

-- pg-boss creates and manages its own schema
```

---

# 7. Metadata system

## 7.1 The provider interface

Every provider implements one interface. Nothing else in the app knows a provider's name.

```ts
interface MetadataProvider {
  id: 'igdb' | 'tmdb' | 'anilist' | 'steam'
  supports: MediaType[]
  search(query: string, opts?): Promise<SearchResult[]>
  getDetails(externalId: string): Promise<ProviderDetails>
  getArtwork(externalId: string): Promise<ProviderArtwork[]>
}

type SearchResult = {
  externalId: string; title: string; year?: number
  coverUrl?: string; summary?: string
}

type ProviderDetails = {
  title: string; altTitles: string[]; description?: string
  releaseDate?: string; runtimeMinutes?: number
  genres: string[]; developer?: string; publisher?: string
  franchise?: string; externalIds: Record<string, string>
  seasons?: { number: number; title?: string; episodes: EpisodeStub[] }[]
  platforms?: string[]
}
```

Adding a provider means one file in `features/metadata/providers/` and one registry entry.

## 7.2 Caching and rate limits

Every outbound call goes through a wrapper that:

1. Hashes `(provider, endpoint, params)` and checks `provider_cache`
2. Returns the cached row if present — during development nothing hits the network twice
3. Otherwise applies the provider's rate limiter (IGDB is ~4 req/sec), calls, and **stores
   the raw response permanently**

IGDB additionally needs a Twitch OAuth client-credentials token, cached in memory with
refresh-on-401.

## 7.3 Field origin — the anti-clobber rule

Every writable field on a `media_item` has a row in `field_origins` recording whether its
current value came from a provider or from you.

```
Title         → provider: igdb
Description   → custom          ← you edited this
Cover         → custom          ← you replaced this
Background    → provider: igdb
Release date  → provider: igdb
Rating        → (personal fields have no origin row; never touched by sync)
```

**On import:** every field written gets `source = provider`.

**On manual edit:** that field flips to `source = custom`.

**On refresh:** the merge walks each incoming field —

```
for field in incoming:
    origin = field_origins[field]
    if origin is missing or origin.source == 'provider':
        write the new value; keep source = provider
    else:                                     # custom
        skip entirely
```

Personal data — rating, status, notes, resume note, favourite, rank, tags, assets — is never
part of a provider merge at all. A "revert to provider value" button on each field deletes
the custom origin row and re-fetches, making the override deliberate in both directions.

## 7.4 Artwork

Provider image URLs are fetched once at import and stored locally under
`storage/artwork/`, hashed like any other file. The database keeps the path; nothing
hotlinks. Replacing artwork manually flips that slot's `field_origins` row to `custom`.

## 7.5 Offline

A failed provider call surfaces as a banner — *"Offline. External metadata providers
unavailable. Your archive is fully available."* — never a page error. Everything except
search, import and refresh works with no network.

---

# 8. File storage system

## 8.1 Layout

```
$STORAGE_PATH/
├── screenshots/ab/cd/abcdef0123….png
├── clips/       ab/cd/abcdef0123….mp4
├── saves/       …
├── documents/   …
├── artwork/     …
├── thumbnails/
│   ├── grid/    ab/cd/abcdef0123….webp     320px
│   ├── preview/ ab/cd/abcdef0123….webp    1280px
│   └── poster/  ab/cd/abcdef0123….webp     clip poster frames
└── packs/2019/  2019-screenshots-001.zip   (yearly packing, §12 phase 8)
```

Paths are **content-addressed**: the SHA-256 of the file, split into two 2-character
directory levels so no directory holds more than a few thousand entries. The original
filename lives in the database for display.

## 8.2 The ingest pipeline

Every file entering the system runs the same seven steps:

```
1. Receive          multipart upload, or a path from the bulk importer
2. Validate         extension + magic bytes against an allowlist; size cap;
                    never trust the client-supplied filename
3. Hash             SHA-256 → if it already exists in `assets`, stop and
                    return the existing record (idempotent re-imports)
4. Extract          images  → EXIF DateTimeOriginal, dimensions
                    video   → ffprobe creation_time, duration, resolution
                    neither → file mtime
                    nothing → now()
5. Store            write to <kind>/<hash[0:2]>/<hash[2:4]>/<hash>.<ext>
6. Derive           Sharp: grid + preview thumbnails
                    FFmpeg: poster frame for clips
7. Record           insert `assets` row, write the JSON sidecar,
                    emit an `asset_added` timeline event
```

Steps 5–7 are one transaction plus a file write; a failure at step 7 leaves an orphaned file
that the nightly maintenance job quarantines.

## 8.3 Sidecars

Beside every stored file sits `<hash>.<ext>.json`:

```json
{
  "hash": "abcdef0123…",
  "kind": "screenshot",
  "original_filename": "Elden Ring 2026-03-04.png",
  "mime_type": "image/png",
  "bytes": 3847221,
  "width": 2560, "height": 1440,
  "capture_date": "2026-03-04T21:14:03Z",
  "item": { "type": "game", "title": "Elden Ring", "igdb_id": "1234" },
  "album": "Boss fights",
  "title": "Malenia, finally",
  "tags": ["boss", "victory"],
  "note": "took 47 tries"
}
```

This is what makes principle 5 true: with the database gone, a script can walk
`$STORAGE_PATH`, read the sidecars and rebuild the asset catalogue.

## 8.4 Albums

An album is a named folder of assets inside a single item — `Skills`, `Boss drops`,
`Funny deaths`. Assets carry an optional `album_id`; the item's Screenshots and Clips tabs
group by album with an "Unsorted" bucket. Bulk import can target an album directly, which is
how a large organised collection for one game gets in.

## 8.5 Serving

Thumbnails are served directly by Next.js from disk with long cache headers. Originals are
served through an authenticated route that resolves the hash to a path — nothing under
`$STORAGE_PATH` is publicly routable.

---

# 9. API surface

All routes require a session except `/api/health`. All bodies validated with the Zod schema
shared by the corresponding form.

```
GET    /api/health

POST   /api/auth/login
POST   /api/auth/logout

GET    /api/items                 ?type&status&platform&genre&tag&favorite
                                  &q&sort&order&page&limit
POST   /api/items
GET    /api/items/:id
PATCH  /api/items/:id
DELETE /api/items/:id
POST   /api/items/:id/status
POST   /api/items/:id/rating
POST   /api/items/:id/artwork/:kind
POST   /api/items/:id/refresh              provider merge, §7.3
POST   /api/items/:id/fields/:field/revert

GET    /api/items/:id/platforms
POST   /api/items/:id/platforms
PATCH  /api/platforms/:id
POST   /api/items/:id/sessions

GET    /api/items/:id/seasons
POST   /api/episodes/:id/watch
DELETE /api/episodes/:id/watch
POST   /api/items/:id/watch                movies

GET    /api/items/:id/albums
POST   /api/items/:id/albums
PATCH  /api/albums/:id
DELETE /api/albums/:id

GET    /api/assets                ?kind&itemId&albumId&unassigned&page
POST   /api/assets                multipart, §8.2
GET    /api/assets/:id
PATCH  /api/assets/:id            title, item, album, tags, note
DELETE /api/assets/:id
GET    /api/assets/:id/file
GET    /api/assets/:id/thumb/:size

POST   /api/import/stage          upload a batch, returns previews
POST   /api/import/commit         assign groups to items/albums

GET    /api/providers/search      ?provider&type&q
GET    /api/providers/details     ?provider&externalId
POST   /api/providers/import      create an item from a provider result
POST   /api/providers/steam/sync

GET    /api/achievements          ?itemId
POST   /api/achievements/sync     ?source=steam|retroachievements

GET    /api/cards
GET    /api/cards/sets
GET    /api/prestige              ?itemId
POST   /api/prestige
POST   /api/prestige/:id/evidence

GET    /api/timeline              ?from&to&type&view=list|calendar
GET    /api/timeline/on-this-day
GET    /api/memories
POST   /api/memories

GET    /api/collections
POST   /api/collections
GET    /api/collections/:id/items

GET    /api/bounties
POST   /api/bounties
POST   /api/bounties/:id/complete

GET    /api/search                ?q          global, all entity types
GET    /api/stats
GET    /api/stats/year/:year

GET    /api/settings
PATCH  /api/settings
GET    /api/health/data                      data health report
POST   /api/maintenance/run                  manual trigger
```

---

# 10. UI specification

## 10.1 Navigation

```
┌────────────┬──────────────────────────────────────────────┐
│  ARCHIVE   │  [ search…            ⌘K ]      [+ Upload]   │
│            ├──────────────────────────────────────────────┤
│  Home      │                                              │
│            │                                              │
│  GAMES     │                content                       │
│  Movies    │                                              │
│  TV        │                                              │
│  Anime     │                                              │
│            │                                              │
│  Backlog   │                                              │
│  Cards     │                                              │
│            │                                              │
│  Archive   │                                              │
│  Inbox  ⑿ │                                              │
│            │                                              │
│  Timeline  │                                              │
│  Stats     │                                              │
│            │                                              │
│  Settings  │                                              │
└────────────┴──────────────────────────────────────────────┘
```

Sidebar collapses to icons; on mobile it becomes a bottom bar with Home / Library / Upload /
Timeline / More. The Inbox badge shows unassigned asset count.

## 10.2 Library (all four types share one component)

```
Games                                     1,284 items

[Platform ▾] [Status ▾] [Genre ▾] [Sort ▾]        [▦ ▤]

┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│        │ │        │ │        │ │        │ │        │
│ COVER  │ │ COVER  │ │ COVER  │ │ COVER  │ │ COVER  │
│        │ │        │ │        │ │        │ │        │
│ ★ ＋ ⋮ │ │        │ │        │ │        │ │        │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘
Elden Ring  Hades      Hollow K…  Outer Wi…  Celeste
★ 9.4       ★ 9.1      ★ 9.6      ★ 9.8      ★ 8.9
```

- Cards are artwork-first: cover, title, one stat. Nothing else.
- Hover reveals ★ favourite, ＋ add to collection, ⋮ menu
  (Open · Edit · Add Screenshot · Add Clip · Change Status · Add to Collection ·
  Refresh Metadata · Delete)
- Hovering blooms the cover into a blurred page background
- ▦ / ▤ switches to a dense table view
- Infinite scroll, 60 per page, grid virtualised past ~500 items

## 10.3 Game detail

```
┌──────────────────────────────────────────────────────────┐
│                    HERO ARTWORK                          │
│  ┌──────┐                                                │
│  │COVER │  ELDEN RING                          [Edit]    │
│  │      │  ★ 9.4  ·  #7  ·  Playing                      │
│  └──────┘  Steam · 143h · 87% · 2 albums                 │
└──────────────────────────────────────────────────────────┘

Overview │ Progress │ Screenshots │ Clips │ Saves │ Docs │ Notes │ Stats

┌─ Overview ──────────────────────────────────────────────┐
│  Description…                                            │
│  Released 2022-02-25 · FromSoftware · Bandai Namco       │
│  Action RPG · Souls-like · Open World                    │
│                                                          │
│  Rating          Story 9.2  Gameplay 9.8  Sound 8.7      │
│                  Presentation 9.0  Enjoyment 9.6         │
│                  Overall 9.3 · confidence High           │
│                                                          │
│  Resume note     "Caelid — find the smithing merchant"   │
│                                                          │
│  Platforms       Steam    143h   87%   [details]         │
│                  PS5       12h    4%   [details]         │
└──────────────────────────────────────────────────────────┘
```

Movies drop Progress, Saves and platform rows. TV and anime replace Progress with a season
and episode list.

## 10.4 Episode tracking (TV / anime)

```
Attack on Titan                              Watching · 43/87

[ Continue → S3E5 ]

Season 1  ████████████████████████  25/25   ✓
Season 2  ████████████████████████  12/12   ✓
Season 3  ██████████░░░░░░░░░░░░░░   6/22

  ☑ 1  Smoke Signal              2018-07-23
  ☑ 2  Pain                      2018-07-30
  ☑ 3  Old Story                 2018-08-06
  ☐ 4  Trust                     2018-08-13
  ☐ 5  Reply                     2018-08-20
```

Clicking a checkbox writes an `episode_watches` row and a timeline event, and advances
Continue.

## 10.5 Quick Capture

Reachable from `[+ Upload]` anywhere.

```
┌── Quick Capture ───────────────────────┐
│  ┌──────────────────────────────────┐  │
│  │        image preview             │  │
│  └──────────────────────────────────┘  │
│  Title    [ Roblox                  ]  │
│  Item     [ none              ▾ ]      │
│  Album    [ —                 ▾ ]      │
│  Date     [ 2026-08-27          ]      │
│  Tags     [ funny               ]      │
│  Note     [                     ]      │
│                    [Cancel] [ Save ]   │
└────────────────────────────────────────┘
```

Item and Album are optional. With no item, it lands in the Inbox. Date pre-fills from EXIF.

## 10.6 Inbox

```
Inbox                                    12 items unassigned

[ Select all ]  [ Assign to item… ]  [ Delete ]

┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│ img │ │ img │ │ img │ │ clip│ │ img │ │ img │
│  ☑  │ │  ☑  │ │     │ │     │ │     │ │     │
└─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘
 Mar 4   Mar 4   Mar 4   Mar 7   Apr 1   Apr 1
```

Select any number → assign to an item, and optionally an album, in one action.

## 10.7 Bulk importer

```
Import                                     100 files staged

Selected: 4                    [ Assign to… ]  [ Clear ]

┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│ ☑   │ │ ☑   │ │ ☑   │ │ ☑   │ │     │ │     │
└─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘

        ┌── Assign 4 files ──────────────┐
        │  Item   [ Elden Ring      ▾ ]  │
        │  Album  [ Boss fights     ▾ ]  │
        │  Tags   [                   ]  │
        │              [ Assign ]        │
        └────────────────────────────────┘
```

Files are staged and thumbnailed on drop, then grouped and assigned manually in batches.
Dates come from EXIF, so the timeline is correct regardless of import order. Duplicates are
detected by hash at stage time and shown greyed out.

## 10.8 Cards

```
Cards                                              23 earned

┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ ╔══════╗ │ │ ╔══════╗ │ │ ╔══════╗ │ │          │
│ ║ ART  ║ │ │ ║ ART  ║ │ │ ║ ART  ║ │ │    ?     │
│ ╚══════╝ │ │ ╚══════╝ │ │ ╚══════╝ │ │          │
│ Hades    │ │ Celeste  │ │ Hollow K │ │  locked  │
│  #07     │ │  #08     │ │  #09     │ │          │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```

Click enlarges; click again flips 180° to the back:

```
        ╔════════════════════════╗
        ║  HADES                 ║
        ║  Completed 2026-04-12  ║
        ║  49 achievements       ║
        ║  Completion   62h      ║
        ║  Playtime     94h      ║
        ║  Score  9.1 · Rank #12 ║
        ║  Prestige: Hell Mode ✓ ║
        ╚════════════════════════╝
```

Hover lift and subtle tilt, optional shine, click-outside to close. All effects respect the
appearance settings and `prefers-reduced-motion`.

## 10.9 Timeline

```
Timeline                              [ List │ Calendar ]

── Today ────────────────────────────────────────────
   🎮  Played Elden Ring · 2h 14m
   📸  Added 3 screenshots to Elden Ring · Boss fights
   ⭐  Rated Hades 9.1

── 24 August ────────────────────────────────────────
   📺  Watched Attack on Titan S3E4
   🏆  Unlocked 4 achievements in Hades
```

Calendar renders the same events as a month grid with per-day dots.

## 10.10 Other screens

**Home** — Continue (games and media rows), recent activity, inbox count, active bounties,
newest card, On This Day when it has something.

**Backlog** — filtered library with priority ordering, estimated time, and a
"What should I play?" control (random · under 10 hours · never played · high priority).

**Achievements** — per game inside the detail page; a global page for recent unlocks and
overall completion.

**Search** — one input, results grouped by entity type: items, assets, achievements, cards,
notes, timeline.

**Stats** — completions, hours, platform breakdown, active months. `Year in Review` at
`/stats/year/[year]` as a full-width presentation.

**Settings** — Appearance (theme, grid density, card size, visible metadata, effects),
Providers (API keys, sync), Storage (paths, usage, packing, export), Data health.

---

# 11. How it all connects

## 11.1 Adding a game from IGDB

```
User types "Elden Ring" in Add Game
   → GET /api/providers/search?provider=igdb&q=Elden Ring
   → provider wrapper: cache miss → rate limiter → IGDB → cache the raw response
   → results with covers

User picks one
   → GET /api/providers/details → cached or fetched
   → IMPORT PREVIEW shows exactly what will be written

User confirms
   → POST /api/providers/import
     ├── insert media_items (type=game)
     ├── insert external_ids (igdb)
     ├── insert field_origins for every written field, source=provider
     ├── insert genres, franchise
     ├── queue job: download artwork → hash → store → insert artwork rows
     └── insert timeline_event (item_added)
   → redirect to /games/:id
```

## 11.2 Editing, then refreshing

```
User rewrites the description
   → PATCH /api/items/:id
     ├── update media_items.description
     ├── upsert field_origins(description) → source=custom
     └── (no timeline event; edits are not activity)

Months later: Refresh Metadata
   → POST /api/items/:id/refresh
   → getDetails from IGDB
   → merge loop (§7.3):
        title        origin=provider → updated
        description  origin=custom   → SKIPPED
        release_date origin=provider → updated
        cover        origin=custom   → SKIPPED
   → rating, status, notes, assets never enter the merge
```

## 11.3 Uploading a screenshot to an album

```
User is on /games/:id, Screenshots tab, album "Boss fights", clicks + Upload
   → POST /api/assets  (multipart; itemId and albumId pre-filled)
   → ingest pipeline (§8.2):
        validate → hash → duplicate? → EXIF date → store →
        thumbnails → insert assets row → write sidecar
   → insert timeline_event (asset_added)
   → the album grid revalidates and the new thumbnail appears
```

## 11.4 Bulk importing an organised folder

```
User drags 240 files onto /import
   → POST /api/import/stage
   → each file: hash, duplicate check, EXIF date, thumbnail into a staging area
   → grid of previews, duplicates greyed out

User selects 60, assigns to Old School RuneScape / album "Boss drops"
   → POST /api/import/commit
   → for each: move from staging into content-addressed storage,
     insert assets row with album_id, write sidecar
   → one timeline_event per import batch, not per file

Repeat per album. Nothing is written until commit.
```

## 11.5 Earning a card

```
Nightly job: achievement sync
   → for each item with external_ids for steam / retroachievements
   → fetch unlocks → upsert achievement_unlocks
   → for RA, follow ParentGameID to pull subsets into their own achievement_sets

After sync, the card check runs per item:
   total   = count(achievements) across ALL sets (core + subset + dlc)
   unlocked = count(achievement_unlocks) for those achievements
   if total > 0 and unlocked == total and no card exists:
       ├── insert cards (platform, counts, playtime, score, rank)
       ├── set media_items.status = 'mastered'
       ├── insert timeline_event (card_minted)
       └── surface it on Home as NEWEST CARD
```

## 11.6 Prestige

```
User adds a prestige challenge to a game
   → POST /api/prestige  { type: 'no_hit', name: 'No-hit run' }
   → status = active, shown on the game page

User uploads a clip as proof
   → normal asset upload, then POST /api/prestige/:id/evidence { assetId }

User marks it complete
   → status = completed, completed_at set
   → timeline_event (prestige_completed)
   → the card back gains a "Prestige: No-hit run ✓" line
```

## 11.7 Bounties

```
Weekly job proposes one:
   pick a media_item where status = 'dropped' or 'paused'
   and last activity > 90 days ago
   → insert bounty { title: "Give Hollow Knight another go" }

Shown on Home. Completing it:
   → POST /api/bounties/:id/complete
   → timeline_event (bounty_completed)

No points, no stakes. It exists to nudge you back to something you left.
```

## 11.8 Nightly maintenance

```
02:00  backup            pg_dump → backups/, prune > 30 days
02:15  orphan files      files on disk with no assets row → quarantine/
02:20  orphan records    assets rows whose file is missing → flag
02:25  staging cleanup   abandoned import batches > 24h
02:30  thumbnails        regenerate any missing
02:35  duplicates        hash scan → report
02:40  database          VACUUM ANALYZE
02:45  report            write result → Data health page
```

Every job reports. Only quarantine moves files, and nothing is deleted automatically.

---

# 12. Build order

Each phase ends in something runnable.

**Phase 0 — Setup.** Tooling installed, repo created, everyone has merged a PR. Glossary and
rating rubric written. Name decided and recorded as ADR 0001.

**Phase 1 — Foundation.** Docker with Postgres, Drizzle migrations, core schema, seed and
reset scripts, `/api/health` green with everything containerised.

**Phase 2 — Design system.** Tokens, shadcn, app shell, `MediaCard`, `LibraryGrid`,
`FilterBar`, `DetailShell`, `EntityForm`, empty states, skeletons. A `/kitchen-sink` page
showing every component in every state, light and dark.

**Phase 3 — Vertical slice.** Auth, items API, games library, game detail, manual add, edit
form, ratings, status, artwork upload, screenshot upload, gallery, timeline event. One game
travels end to end. *This is the milestone that proves the architecture.*

**Phase 4 — Metadata.** Provider interface, cache, rate limiter, IGDB, search → preview →
import, artwork download, field origins, safe refresh, offline banner.

**Phase 5 — Archive.** Storage layer, sidecars, ingest pipeline, EXIF/ffprobe dates,
thumbnails, Quick Capture, Inbox, contextual upload, albums, bulk importer, dedupe,
create-item-from-asset. **Import the real collection here** — oldest year first, verify the
dates, then continue.

**Phase 6 — Media.** TMDB and AniList, movies, seasons and episodes, episode tracking,
continue watching, watch history, the three media libraries.

**Phase 7 — Views.** Home, backlog, what should I play, timeline, calendar, on this day,
collections, global search, memories, personal rank, clips, saves, documents.

**Phase 8 — Deploy.** Production Dockerfile and compose, CI to GHCR, server setup, Tailscale,
nightly backups with a restore test, mobile pass. **Use it daily from here on.**

**Phase 9 — Achievements and cards.** Achievement sets, Steam sync, RetroAchievements with
subsets, achievements UI, card minting, card object and gallery, card sets, prestige.

**Phase 10 — Refinement.** Bounties, statistics, year in review, smart collections, appearance
settings, command palette, maintenance jobs, data health, background jobs, performance pass,
security pass, tests, custom fields, franchises, physical ownership, export bundle, yearly
packing.

---

# 13. Deployment

## Environments

| | Where | Data |
|---|---|---|
| Development | Each dev's PC, `compose.dev.yaml` | Seed data, wipe freely |
| Test | CI, ephemeral containers | Generated per run |
| Production | Home server, `compose.yaml` | The real archive. Never experiment here. |

## Production compose

```yaml
services:
  app:
    image: ghcr.io/<owner>/archive:<version>
    environment:
      DATABASE_URL, AUTH_SECRET, STORAGE_PATH,
      IGDB_CLIENT_ID, IGDB_CLIENT_SECRET, TMDB_API_KEY,
      ANILIST_TOKEN, STEAM_API_KEY, RA_API_KEY
    volumes:
      - /mnt/raid/archive/storage:/storage
    depends_on: [db]
    restart: unless-stopped

  db:
    image: postgres:18
    volumes:
      - /mnt/raid/archive/postgres:/var/lib/postgresql/data
    restart: unless-stopped
```

Persistent data lives outside the containers. Destroying and rebuilding a container never
touches the archive.

## Pipeline

```
feature branch → local Docker test → PR
   → GitHub Actions: lint · typecheck · test · docker build
   → merge → tag → GHCR image
   → you review → server pulls a specific version
```

No automatic production updates. Versions are pinned, never `:latest`.

## Access

The app listens on a port inside Docker and knows nothing about how it's reached. LAN by IP,
or Tailscale from anywhere. It trusts forwarded headers but owns no routing.

## Backups

- Database: nightly `pg_dump`, 30-day retention, **monthly automated restore test**
- Media: the RAID is redundancy, not backup — an off-array copy is required
- Config: compose files and `.env.example` in Git
- Export: `scripts/export.ts` produces a portable bundle

---

# 14. Conventions

**Migrations.** Every schema change is a generated, committed migration. `drop database` is
never part of a workflow.

**Validation.** One Zod schema per entity in `lib/zod/`, imported by both the API route and
the form. Never two definitions of the same shape.

**Feature boundaries.** A module in `features/` may import from `lib/`, `db/` and
`components/`. It may not import from a sibling feature. Shared logic moves to `lib/`.

**Timestamps.** Everything is `timestamptz`, stored UTC, rendered local.

**Deletion.** Always behind a confirm dialog naming what will be lost. Deleting an item asks
explicitly what to do with its assets.

**Errors.** API routes return `{ error: { code, message } }`. The UI renders a toast. No
silent failures.

**Jobs.** Anything that could exceed two seconds goes to pg-boss.

**Definition of done.** Migration · logic · validation · error handling · UI · loading state ·
empty state · mobile · tests · Docker build passes · docs updated · no secrets in source.

**Decisions.** Anything architectural gets a file in `docs/decisions/` recording the
decision, the reason, the alternatives, and the consequences.
