# Frontend ↔ Backend Data Contract

Living list of the data shapes the frontend expects from the backend API. Not a formal spec —
just enough for the backend to build Pydantic models and routes against. Source of truth on the
frontend side is `src/frontend/src/types/game.ts`; this file explains the *why* behind each
field and flags anything that's still a frontend-only placeholder.

Updated as new fields get added on the frontend side — see the change log at the bottom.

## Game

| Field | Type | Notes |
|---|---|---|
| `id` | string (UUID) | Primary identifier |
| `title` | string | |
| `coverColor` | — | **Frontend-only placeholder, not a real backend field.** Stands in for real cover artwork until that exists. |
| `status` | enum: `wishlist \| backlog \| playing \| paused \| completed \| mastered \| dropped` | |
| `ratingOverall` | number \| null | `null` = not rated yet |
| `achievementPercent` | number (0–100) | Could be computed server-side from `achievements` rather than stored as its own column |
| `achievements` | `Achievement[]` | See below |
| `description` | string \| null | |
| `developer` | string \| null | |
| `publisher` | string \| null | |
| `series` | string \| null | `null` when the game isn't part of one |
| `dateAdded` | ISO timestamp string \| null | When this game was added to the tracker — not its real-world release date |
| `tags` | string[] | |
| `platforms` | `GamePlatform[]` | See below. One game can have multiple entries (e.g. owned on both Steam and PS5) — this is the app's real answer to "duplicate games across platforms," not a separate game record per platform |

## GamePlatform

| Field | Type | Notes |
|---|---|---|
| `platform` | string | Free text (`"Steam"`, `"PS5"`, `"Xbox"`, `"Xbox Series X"`, etc.), not an enum — real platform names vary too much to lock down |
| `playtimeMinutes` | number | |
| `completionPercent` | number \| null | `null` when completion isn't tracked on that platform |
| `lastPlayedAt` | ISO timestamp string \| null | `null` = never played on this platform |

## Achievement

| Field | Type | Notes |
|---|---|---|
| `id` | string | |
| `name` | string | |
| `unlockedAt` | ISO timestamp string \| null | `null` = still locked. **Currently mock data on the frontend** — real values need a Steam/RetroAchievements sync, see `Notes/DESIGN.md` §6.6, §11.5 |

## Scope note

Movies, TV, and anime are **cut** from this project — games (and the archive of
screenshots/clips/saves/documents attached to them) only. Everything else in `Notes/DESIGN.md`
(achievements, cards, prestige, backlog/bounties, timeline, collections, stats) is still the
long-term plan, just not all built yet.

## Change log

- 2026-08-30 — initial version: `Game` + `Achievement` shapes
- 2026-08-30 — added `description`/`developer`/`publisher`/`tags`/`playtimeMinutes`/`lastPlayedAt`; `unlockedAt`/`lastPlayedAt` upgraded from date-only to full ISO timestamps; noted planned multi-platform support as not-yet-modeled
- 2026-08-31 — replaced flat `playtimeMinutes`/`lastPlayedAt` on `Game` with `platforms: GamePlatform[]`, adding real Xbox/PlayStation support and multi-platform ownership for one game; confirmed scope: movies/TV/anime cut, rest of `DESIGN.md` stays