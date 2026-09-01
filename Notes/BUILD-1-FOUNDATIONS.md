# Build Manual — Part 1: Foundations

*Concepts, setup, Docker, and the database. Read this before touching code.*

**The series:**
1. **Foundations** ← you are here
2. Backend — auth, validation, API, the list engine, metadata providers
3. Assets — storage, ingest, import, achievements, cards, jobs
4. Frontend & Operations — UI, search, testing, CI, deployment

---

# 0. How to read this

This manual assumes you can write basic JavaScript and have used a terminal, and assumes
nothing else. Every concept gets explained the first time it appears.

Three things to know before starting:

**You will not understand everything on the first pass.** That's normal and it's fine. Build
the thing, and understanding arrives through repetition.

**Never merge code you can't explain.** If an AI assistant or Stack Overflow hands you
something and you can't say what each line does, you can't debug it at 11pm in month seven.
Ask until you can explain it.

**When you're stuck for 30 minutes, stop and ask.** Post the exact error text and what you
tried. Beginners lose entire weekends to things another person spots in ninety seconds.

---

# 1. The concepts

Skip anything you already know.

## 1.1 What the app physically is

A **web server** is a program that listens on a port, receives HTTP requests, and sends back
responses. Ours listens on port 3000 and answers two kinds of request:

- *"Give me the HTML for the games page"* → it renders a page and sends it
- *"Give me the JSON list of my games"* → it queries the database and sends data

**Next.js** is the framework that handles both. You write React components for the pages and
plain functions for the data endpoints, and Next.js wires up the HTTP part.

**PostgreSQL** is a separate program that stores data in tables and answers queries. Our app
talks to it over a network connection, even when both are on the same machine.

So the running system is two processes:

```
  browser ──HTTP──> Next.js app ──SQL──> PostgreSQL
                         │
                         └──file reads/writes──> the storage folder
```

Files (screenshots, clips) never go in the database. They sit on disk, and the database holds
their *paths*. This is important — databases are bad at large binary data, and putting a
2 GB clip in a table would make backups impossible.

## 1.2 Containers, images, volumes

A **container** is a running program packaged with its own filesystem, so it behaves
identically on your laptop and on the server. An **image** is the frozen template a container
is created from.

The critical thing to internalise: **a container's filesystem is thrown away when the
container is destroyed.** That's a feature — it means you can rebuild cleanly — but it means
anything you want to keep must live in a **volume**, which is a folder on the host machine
mapped into the container.

```
Host machine                        Container
/mnt/raid/archive/postgres   <───>  /var/lib/postgresql/data
/mnt/raid/archive/storage    <───>  /storage
```

Destroy and recreate the container: the data is untouched, because it was never inside the
container.

**Docker Compose** describes several containers and how they connect, in one YAML file. Ours
describes two: the app and the database.

Inside a Compose network, containers reach each other **by service name**. That's why the
app's database URL says `@db:5432` — `db` is the service name, not a hostname you configured.
From your laptop's browser it's `localhost:5432` instead, because you're outside that network.
This trips up everyone once.

## 1.3 The database vocabulary

A **table** is a grid. Columns are fields, rows are records.

A **primary key** uniquely identifies a row. We use **UUIDs** — random 128-bit identifiers
like `a3f8...` — rather than counting numbers, because UUIDs can be generated anywhere without
coordination and don't leak how many records you have.

A **foreign key** is a column holding another table's primary key. `assets.game_id` holds a
`games.id`. The database *enforces* that the referenced row exists, which is how you avoid
screenshots pointing at games that were deleted.

**ON DELETE** tells the database what to do when the referenced row disappears:

| Setting | Behaviour | Where we use it |
|---|---|---|
| `cascade` | Delete the child rows too | Artwork, achievements — meaningless without their game |
| `set null` | Blank the reference, keep the row | Assets — a screenshot survives its game and lands in the Inbox |
| `restrict` | Refuse the delete | Not used here |

An **index** is a lookup structure that makes searching a column fast. Without one, finding
all games with `status = 'playing'` means reading every row. With one, the database jumps
straight there. Indexes cost disk space and make writes slightly slower — worth it on anything
you filter or sort by, not worth it on everything.

An **enum** is a column that only accepts values from a fixed list. `status` can be
`'playing'` but never `'plying'`. The database rejects typos rather than storing them.

A **transaction** groups several writes so they all succeed or all fail. When minting a card
we insert the card, update the game's status, and write a timeline event. If the third fails,
you don't want the first two to have happened — a transaction guarantees that.

**Migrations** are versioned files describing schema changes. Rather than editing tables by
hand, you generate a file, commit it to Git, and every machine runs the same files in the same
order. This is what keeps three developers' databases identical, and it's what lets the
production database evolve without being rebuilt.

## 1.4 The TypeScript layer

**TypeScript** is JavaScript with type annotations checked before the code runs. It catches a
huge class of mistakes — misspelled properties, wrong argument order, forgetting a value can be
null — at the moment you type them rather than when a user hits the page.

**Drizzle** is our **ORM** (object–relational mapper): you describe tables in TypeScript, and
it generates migrations, builds queries, and gives you typed results. `game.titel` becomes a
red squiggle instead of `undefined` at runtime.

**Zod** validates data at runtime. TypeScript disappears when the code runs, so it can't
protect you from a malformed request body. Zod checks the actual incoming data against a
schema and rejects what doesn't fit. We define each schema once and use it in two places — the
API route and the form — so they can never disagree about what's valid.

## 1.5 Hashing

A **hash function** turns any input into a fixed-length fingerprint. We use **SHA-256**, which
produces 64 hex characters.

Two properties matter to us:

1. **Identical input → identical hash.** Same file, same fingerprint, every time.
2. **Different input → different hash**, in practice always.

That gives us three features almost for free:

- **Duplicate detection** — hash a file, look for that hash, done. No filename comparison.
- **Idempotent imports** — re-drop the same folder and nothing duplicates.
- **Integrity checking** — re-hash a file later; if the fingerprint changed, the file is
  corrupt.

It's also why we name stored files by their hash: two files can never collide, and a file's
path never needs to change.

---

# 2. Accounts and installs

## 2.1 On every machine

| Tool | Why |
|---|---|
| **Git** | Version control |
| **Node.js LTS** | Runs the app. Install via `nvm` or `fnm` so all three of you match |
| **Docker Desktop** | Runs Postgres and the app in containers |
| **VS Code** | Editor. Extensions: ESLint, Prettier, Tailwind CSS IntelliSense, Docker |
| **TablePlus or DBeaver** | A GUI for looking inside the database. You'll use this constantly |

Note that FFmpeg is **not** in that list. It lives inside the app container, so nobody has to
install it locally.

Verify:

```bash
git --version        # 2.x
node --version       # v22.x or whatever LTS is current
docker --version     # 27.x
docker compose version
```

## 2.2 API credentials

Put these in a shared password manager. Never in Git.

### IGDB

IGDB is owned by Twitch, so authentication goes through Twitch.

1. Go to the Twitch developer console, register an application
2. OAuth redirect URL: `http://localhost` (unused, but required)
3. Category: Application Integration
4. Save the **Client ID**, then generate and save a **Client Secret**

The secret is shown once. If you lose it, generate a new one.

### Steam

1. Get a Steam Web API key from Valve's developer page
2. Find your **SteamID64** — the 17-digit number. Your profile URL may show a vanity name
   instead; a SteamID lookup site converts it
3. Your profile and game details must be **public** or the API returns nothing. This is the
   single most common "why is it empty" cause

### RetroAchievements

Your API key and username are in your RA account settings under Keys.

---

# 3. Bootstrap the project

## 3.1 Create it

```bash
npx create-next-app@latest archive \
  --typescript --tailwind --eslint --app --src-dir=false \
  --import-alias "@/*"

cd archive
```

What those flags mean:

- `--typescript` — TypeScript rather than plain JS
- `--tailwind` — Tailwind CSS preconfigured
- `--app` — the App Router (folder-based routing, the current Next.js model)
- `--src-dir=false` — code at the repo root, not inside `src/`. One less folder level
- `--import-alias "@/*"` — lets you write `import { db } from '@/db'` instead of
  `'../../../db'`. You will be very glad of this

## 3.2 Dependencies

```bash
# database
npm i drizzle-orm postgres
npm i -D drizzle-kit

# validation and forms
npm i zod react-hook-form @hookform/resolvers

# media processing
npm i sharp exifr

# background jobs
npm i pg-boss

# auth
npm i bcrypt
npm i -D @types/bcrypt

# data fetching in the browser
npm i @tanstack/react-query

# helpers
npm i clsx tailwind-merge lucide-react date-fns

# dev tooling
npm i -D tsx vitest prettier prettier-plugin-tailwindcss
npm i -D @playwright/test testcontainers
```

Why each one:

- **drizzle-orm** builds queries and types results. **postgres** is the actual driver that
  speaks the Postgres wire protocol. **drizzle-kit** generates migrations — dev-only, so `-D`
- **zod** validates at runtime. **react-hook-form** manages form state without re-rendering
  the whole form on every keystroke. **@hookform/resolvers** connects the two
- **sharp** resizes images, and it's fast — a screenshot thumbnail takes about 100ms, which is
  why we don't need a job queue for it
- **exifr** reads EXIF metadata (camera info, capture dates) from images
- **pg-boss** is a job queue that stores jobs in Postgres, so no Redis container
- **bcrypt** hashes passwords slowly on purpose, making brute-force attacks expensive
- **@tanstack/react-query** handles browser-side fetching, caching and refetching
- **clsx** + **tailwind-merge** combine CSS classes correctly when they conflict
- **tsx** runs TypeScript files directly, for our scripts

`-D` means *dev dependency* — needed to build and test, not shipped in the production image.

## 3.3 shadcn/ui

```bash
npx shadcn@latest init

npx shadcn@latest add button card dialog dropdown-menu input select \
  tabs tooltip badge sonner skeleton form label textarea checkbox \
  popover command sheet separator scroll-area alert-dialog progress radio-group
```

**shadcn/ui is not a dependency.** It copies component source files into your project, and
you own them. When you need the button to behave differently, you edit the file — there's no
library to fight. Underneath it uses Radix UI, which handles the genuinely hard parts of
components (keyboard navigation, focus trapping, screen-reader semantics) so you get those for
free.

Two of these are load-bearing: `command` becomes the ⌘K palette, and `alert-dialog` is the
delete confirmation — the one that replaced the trash system.

## 3.4 Scripts

In `package.json`:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "typecheck": "tsc --noEmit",
    "format": "prettier --write .",
    "test": "vitest run",
    "test:e2e": "playwright test",
    "db:generate": "drizzle-kit generate",
    "db:migrate": "tsx db/migrate.ts",
    "db:seed": "tsx db/seed.ts",
    "db:reset": "tsx db/reset.ts && npm run db:migrate && npm run db:seed",
    "db:studio": "drizzle-kit studio"
  }
}
```

`typecheck` runs the TypeScript compiler with `--noEmit` — it checks types and produces no
output files. This runs in CI and catches the errors your editor might have been ignoring.

## 3.5 Prettier

`.prettierrc`:

```json
{
  "semi": false,
  "singleQuote": true,
  "printWidth": 90,
  "plugins": ["prettier-plugin-tailwindcss"]
}
```

Agree these once and never discuss formatting again. The Tailwind plugin sorts class names
into a consistent order, which stops PRs full of reordered classes.

---

# 4. Environment and Docker

## 4.1 `.env.example`

Commit this file with empty values. Everyone copies it to `.env` and fills theirs in.

```bash
# ---- database ----
POSTGRES_USER=archive
POSTGRES_PASSWORD=changeme
POSTGRES_DB=archive
DATABASE_URL=postgres://archive:changeme@localhost:5432/archive

# ---- auth ----
AUTH_SECRET=                 # generate: openssl rand -base64 32
ADMIN_USERNAME=admin
ADMIN_PASSWORD=              # used once, on first seed

# ---- storage ----
STORAGE_PATH=./storage

# ---- providers ----
IGDB_CLIENT_ID=
IGDB_CLIENT_SECRET=
STEAM_API_KEY=
STEAM_ID64=
RA_USERNAME=
RA_API_KEY=
```

Then:

```bash
cp .env.example .env
echo ".env" >> .gitignore
git status                   # CONFIRM .env is not listed
```

> **The single most common beginner disaster is committing secrets.** Once a secret is in Git
> history it is effectively public forever, even if you delete it in a later commit — the old
> commit still contains it. Check `git status` before your first commit, every time, until it's
> reflex.

Reading the `DATABASE_URL` format:

```
postgres://archive:changeme@localhost:5432/archive
           ───┬───  ───┬───  ────┬──── ─┬── ───┬───
            user    password   host   port   database
```

From your laptop it's `localhost`. From inside the app container it's `db` — the Compose
service name. Same database, two addresses depending on where you're standing.

## 4.2 `compose.dev.yaml`

```yaml
services:
  db:
    image: postgres:18
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      retries: 10

  app:
    build:
      context: .
      target: dev
    command: npm run dev
    environment:
      DATABASE_URL: postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      STORAGE_PATH: /storage
    env_file:
      - .env
    ports:
      - "3000:3000"
    volumes:
      - .:/app
      - /app/node_modules
      - ./storage:/storage
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
```

Line by line, the parts that aren't obvious:

**`ports: "5432:5432"`** — maps host port 5432 to container port 5432, so your database GUI
can connect from your laptop. Format is `host:container`.

**`volumes: pgdata:/var/lib/postgresql/data`** — a *named volume*, managed by Docker. This is
where Postgres actually stores everything. It survives `docker compose down`. It does **not**
survive `docker compose down -v`, which is the command that deletes your data. Be careful with
that flag.

**`healthcheck`** — Postgres accepts connections a second or two after the container starts.
Without this, the app starts first, fails to connect, and crashes. `pg_isready` is a Postgres
utility that reports whether the server is actually accepting connections.

**`depends_on: condition: service_healthy`** — waits for that healthcheck to pass, not just
for the container to exist. Without `condition`, `depends_on` only waits for the container to
start, which isn't the same thing.

**`volumes: - .:/app` and `- /app/node_modules`** — the first mounts your project folder into
the container so edits appear instantly (hot reload). The second is the trick that makes it
work: it masks `node_modules` with an empty container-side volume. Otherwise your host's
`node_modules` — possibly built for macOS — would shadow the container's Linux build, and
native modules like `sharp` and `bcrypt` would fail with confusing errors.

## 4.3 `Dockerfile`

```dockerfile
# ============ base ============
FROM node:22-slim AS base
RUN apt-get update && apt-get install -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# ============ dev ============
FROM base AS dev
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 3000

# ============ build ============
FROM base AS build
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ============ production ============
FROM base AS prod
ENV NODE_ENV=production
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
COPY --from=build /app/db/migrations ./db/migrations
RUN useradd -m -u 1001 archive \
    && mkdir -p /storage \
    && chown -R archive /storage /app
USER archive
EXPOSE 3000
CMD ["node", "server.js"]
```

**Multi-stage builds.** Each `FROM` starts a new stage. The final image contains only what the
last stage holds, so build tools and source code don't ship to production. Result: a smaller
image and a smaller attack surface.

**`node:22-slim`** — the slim variant is a few hundred MB smaller than the default and has
everything we need.

**`ffmpeg`** — installed once in `base`, inherited by every stage. This is where `ffprobe`
comes from for reading clip duration and resolution.

**`rm -rf /var/lib/apt/lists/*`** — deletes the package index in the same layer that created
it. Docker layers are immutable, so cleaning up in a later `RUN` wouldn't shrink the image.

**`COPY package*.json` before `COPY . .`** — Docker caches each layer and reuses it if its
inputs haven't changed. Copying just the package files first means `npm ci` is only re-run when
dependencies actually change, not on every source edit. This turns a two-minute rebuild into a
five-second one.

**`npm ci`** rather than `npm install` — installs exactly what `package-lock.json` specifies,
reproducibly, and fails if the lockfile is out of sync. Always `ci` in Docker and CI.

**`USER archive`** — the container runs as an unprivileged user, not root. If someone finds a
way to execute code through a file upload, they land as a user who can barely do anything.

**`output: 'standalone'`** — add this to `next.config.js`:

```js
module.exports = { output: 'standalone' }
```

It makes Next.js emit a self-contained `server.js` with only the `node_modules` actually
imported, rather than all of them. Much smaller image.

## 4.4 First run

```bash
docker compose -f compose.dev.yaml up
```

Expect the first build to take a few minutes. When it settles you should see Postgres logging
"ready to accept connections" and Next.js logging "Ready on http://localhost:3000".

### When it doesn't work

| Symptom | Cause and fix |
|---|---|
| `port is already allocated` | Something else uses 5432 or 3000 — likely a locally installed Postgres. Stop it, or change the host side: `"5433:5432"` |
| `ECONNREFUSED db:5432` | The app started before the database was ready. Check the healthcheck block exists and `depends_on` uses `condition` |
| `Cannot find module 'sharp'` | The `node_modules` masking volume is missing or you built on the host. `docker compose down && docker compose build --no-cache` |
| Edits don't appear | The `.:/app` volume is missing, or you're on Docker Desktop for Windows outside WSL2 — move the project inside the WSL filesystem |
| `permission denied` on `/storage` | The host folder is owned by root. `mkdir -p storage && chmod 777 storage` locally |

**Checkpoint:** all three of you can run `docker compose -f compose.dev.yaml up` and load
`http://localhost:3000`. Don't move on until that's true for everyone.

---

# 5. The database layer

## 5.1 Wiring Drizzle

`drizzle.config.ts` at the repo root — this is for the migration generator, not the app:

```ts
import type { Config } from 'drizzle-kit'

export default {
  schema: './db/schema.ts',      // where your table definitions live
  out: './db/migrations',        // where generated SQL is written
  dialect: 'postgresql',
  dbCredentials: { url: process.env.DATABASE_URL! },
} satisfies Config
```

The `!` after `process.env.DATABASE_URL` is TypeScript's non-null assertion — "I promise this
isn't undefined." Use it sparingly; here it's correct, because the app genuinely cannot start
without a database URL.

`db/index.ts` — this is what the app imports:

```ts
import { drizzle } from 'drizzle-orm/postgres-js'
import postgres from 'postgres'
import * as schema from './schema'

const client = postgres(process.env.DATABASE_URL!, { max: 10 })

export const db = drizzle(client, { schema })
export type DB = typeof db
```

**`max: 10`** is the connection pool size. Opening a database connection is expensive
(hundreds of milliseconds), so the pool keeps ten open and hands them out as needed. Ten is
plenty for a single-user app; the risk of a large number is exhausting Postgres's own
connection limit.

Passing `{ schema }` is what enables the query API (`db.query.games.findFirst(...)`) with
full type inference and relation loading.

## 5.2 Writing the schema

Everything lives in `db/schema.ts`. Enums first, because tables reference them.

```ts
import {
  pgTable, pgEnum, uuid, text, integer, numeric, boolean,
  timestamp, date, jsonb, index, uniqueIndex, serial,
} from 'drizzle-orm/pg-core'
import { sql, relations } from 'drizzle-orm'

export const gameStatus = pgEnum('game_status', [
  'wishlist', 'backlog', 'playing', 'paused',
  'completed', 'mastered', 'dropped',
])
```

`pgEnum` creates a real Postgres type. The database itself will reject any other value, which
means a bug in your code becomes a loud error instead of silently corrupt data.

> **Enums are hard to change later.** Adding a value is easy (`ALTER TYPE ... ADD VALUE`);
> removing or reordering means recreating the type and rewriting every column that uses it.
> Spend a few minutes agreeing on these lists now.

The rest:

```ts
export const priority       = pgEnum('priority', ['low', 'normal', 'high'])
export const confidence     = pgEnum('confidence', ['low', 'medium', 'high'])
export const providerName   = pgEnum('provider', ['igdb', 'steam', 'retroachievements'])
export const originSource   = pgEnum('origin_source', ['provider', 'custom'])
export const artworkKind    = pgEnum('artwork_kind',
  ['cover', 'background', 'logo', 'icon', 'banner'])
export const assetKind      = pgEnum('asset_kind',
  ['screenshot', 'clip', 'save', 'document'])
export const clipType       = pgEnum('clip_type',
  ['gameplay', 'achievement', 'highlight', 'funny', 'other'])
export const assetSource    = pgEnum('asset_source',
  ['manual', 'medal', 'imported', 'other'])
export const setKind        = pgEnum('set_kind', ['core', 'subset', 'dlc'])
export const ownedFormat    = pgEnum('owned_format',
  ['digital', 'physical', 'both', 'none'])
export const challengeState = pgEnum('challenge_state',
  ['active', 'completed', 'abandoned'])
export const collectionKind = pgEnum('collection_kind', ['manual', 'smart'])
export const relationKind   = pgEnum('relation_kind',
  ['sequel_of', 'prequel_of', 'remake_of', 'port_of', 'spin_off_of'])
export const eventType      = pgEnum('event_type', [
  'game_added', 'status_changed', 'rating_changed', 'asset_added',
  'achievement_unlocked', 'card_minted', 'prestige_completed',
  'session_logged', 'bounty_completed',
])
```

Shared columns, so you don't retype them thirty times:

```ts
const timestamps = {
  createdAt: timestamp('created_at', { withTimezone: true })
    .notNull().defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true })
    .notNull().defaultNow(),
}
```

**Always `withTimezone: true`.** A timestamp without a timezone is ambiguous — it says "3pm"
without saying where. Store UTC, render local. Getting this wrong means your timeline silently
shifts by hours when the server's timezone differs from yours, or when daylight saving changes.

### The `games` table

```ts
export const games = pgTable('games', {
  id: uuid('id').primaryKey().defaultRandom(),

  title: text('title').notNull(),
  sortTitle: text('sort_title').notNull(),
  altTitles: jsonb('alt_titles').$type<string[]>().default([]),
  description: text('description'),
  releaseDate: date('release_date'),
  developer: text('developer'),
  publisher: text('publisher'),

  status: gameStatus('status').notNull().default('backlog'),
  priority: priority('priority'),
  favorite: boolean('favorite').notNull().default(false),
  personalRank: integer('personal_rank'),

  ratingStory:        numeric('rating_story', { precision: 3, scale: 1 }),
  ratingGameplay:     numeric('rating_gameplay', { precision: 3, scale: 1 }),
  ratingSoundtrack:   numeric('rating_soundtrack', { precision: 3, scale: 1 }),
  ratingPresentation: numeric('rating_presentation', { precision: 3, scale: 1 }),
  ratingEnjoyment:    numeric('rating_enjoyment', { precision: 3, scale: 1 }),
  ratingOverall:      numeric('rating_overall', { precision: 3, scale: 2 }),
  ratingConfidence:   confidence('rating_confidence'),

  notes: text('notes'),
  resumeNote: text('resume_note'),

  ...timestamps,
}, (t) => ({
  statusIdx:   index('games_status_idx').on(t.status),
  sortIdx:     index('games_sort_title_idx').on(t.sortTitle),
  favoriteIdx: index('games_favorite_idx').on(t.favorite),
  rankIdx:     index('games_rank_idx').on(t.personalRank),
}))
```

Decisions worth understanding:

**`sortTitle` separate from `title`.** Displays as *The Legend of Zelda*, sorts as
*Legend of Zelda, The*. Computed on save by stripping leading articles. Without it, half your
library files under T.

**`altTitles` as `jsonb`.** A proper table would be more "correct", but you never query by
alternate title independently — you only ever read them alongside the game. JSONB is the right
call when data is a list you always fetch as a unit.

**`.$type<string[]>()`** tells TypeScript what shape that JSONB holds. Postgres stores
arbitrary JSON; this is purely so your editor knows it's an array of strings.

**`numeric` rather than `float` for ratings.** Floating-point numbers can't represent decimals
exactly — the classic `0.1 + 0.2 = 0.30000000000000004`. `numeric` stores exact decimals.
`precision: 3, scale: 1` means three total digits, one after the point: up to `99.9`, which
comfortably covers 0–10.

**`ratingOverall` is a stored column, not computed by the database.** We compute it in
application code because the weights are configurable. If it were a generated column, changing
a weight would need a migration.

**`notNull().default(...)` vs. nullable.** `status` is always known, so it's not-null with a
default. `priority` genuinely might not be set, so it's nullable. Be deliberate: nullable
columns force every consumer to handle the null case.

### Foreign keys and delete behaviour

```ts
export const externalIds = pgTable('external_ids', {
  id: uuid('id').primaryKey().defaultRandom(),
  gameId: uuid('game_id').notNull()
    .references(() => games.id, { onDelete: 'cascade' }),
  provider: providerName('provider').notNull(),
  externalId: text('external_id').notNull(),
  url: text('url'),
  ...timestamps,
}, (t) => ({
  uniq: uniqueIndex('external_ids_game_provider_uniq')
    .on(t.gameId, t.provider),
  lookup: index('external_ids_lookup_idx')
    .on(t.provider, t.externalId),
}))
```

**`onDelete: 'cascade'`** — delete the game and its external IDs go too. Correct here: an IGDB
ID for a game that no longer exists is garbage.

**The unique index on `(gameId, provider)`** enforces one IGDB ID per game. Without it, a
buggy import could attach three different IGDB IDs to one game and nothing would complain.

**The second index on `(provider, externalId)`** serves the reverse lookup — "which game has
Steam appid 1245620?" — which is exactly what the Steam sync does, once per owned game. Without
it, that sync gets slower as your library grows.

```ts
export const artwork = pgTable('artwork', {
  id: uuid('id').primaryKey().defaultRandom(),
  gameId: uuid('game_id').notNull()
    .references(() => games.id, { onDelete: 'cascade' }),
  kind: artworkKind('kind').notNull(),
  fileHash: text('file_hash').notNull(),
  path: text('path').notNull(),
  width: integer('width'),
  height: integer('height'),
  bytes: integer('bytes'),
  source: originSource('source').notNull().default('provider'),
  ...timestamps,
}, (t) => ({
  uniq: uniqueIndex('artwork_game_kind_uniq').on(t.gameId, t.kind),
}))
```

One cover per game, one background per game — that's what the unique index on
`(gameId, kind)` says. Replacing artwork is an upsert, not an insert, so you can't
accumulate three covers.

### The assets table

This is the one with interesting delete semantics.

```ts
export const assets = pgTable('assets', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: uuid('user_id').notNull().references(() => users.id),
  kind: assetKind('kind').notNull(),

  gameId: uuid('game_id')
    .references(() => games.id, { onDelete: 'set null' }),
  gamePlatformId: uuid('game_platform_id')
    .references(() => gamePlatforms.id),
  albumId: uuid('album_id')
    .references(() => albums.id, { onDelete: 'set null' }),

  title: text('title'),
  fileHash: text('file_hash').notNull().unique(),
  path: text('path').notNull(),
  originalFilename: text('original_filename').notNull(),
  mimeType: text('mime_type').notNull(),
  bytes: integer('bytes').notNull(),
  width: integer('width'),
  height: integer('height'),
  durationSeconds: numeric('duration_seconds', { precision: 10, scale: 3 }),
  captureDate: timestamp('capture_date', { withTimezone: true }).notNull(),

  clipType: clipType('clip_type'),
  source: assetSource('source').notNull().default('manual'),
  saveType: text('save_type'),
  restoreNotes: text('restore_notes'),
  note: text('note'),

  ...timestamps,
}, (t) => ({
  byGame:  index('assets_game_capture_idx').on(t.gameId, t.captureDate),
  byKind:  index('assets_kind_capture_idx').on(t.kind, t.captureDate),
  byAlbum: index('assets_album_idx').on(t.albumId),
}))
```

**`gameId` is nullable with `onDelete: 'set null'`.** This single choice is what makes the
Inbox work and what makes principle 4 real. A screenshot with no game is valid. Delete a game
and its screenshots aren't destroyed — they fall back to the Inbox, where you can reassign
them.

**`fileHash` is unique.** The database itself guarantees you can never store the same file
twice. Even if two import paths race each other, one insert fails rather than creating a
duplicate.

**`captureDate` is not-null** — the ingest pipeline always produces one, falling back through
EXIF → ffprobe → file mtime → now. Making it not-null means the timeline never has to handle
missing dates.

**The composite index `(gameId, captureDate)`** serves the query "screenshots for this game,
newest first," which is the single most-run query in the app. Column order matters: Postgres
can use a composite index for the leading column alone, but not for the trailing one alone.

## 5.3 Relations

Drizzle needs relations declared separately from tables in order to load nested data:

```ts
export const gamesRelations = relations(games, ({ many }) => ({
  platforms: many(gamePlatforms),
  artwork: many(artwork),
  externalIds: many(externalIds),
  assets: many(assets),
  albums: many(albums),
  achievementSets: many(achievementSets),
}))

export const assetsRelations = relations(assets, ({ one }) => ({
  game: one(games, { fields: [assets.gameId], references: [games.id] }),
  album: one(albums, { fields: [assets.albumId], references: [albums.id] }),
}))
```

Now you can write:

```ts
const game = await db.query.games.findFirst({
  where: eq(games.id, id),
  with: { platforms: true, artwork: true },
})
```

and `game.platforms` is typed as an array of platform rows. Note that relations are metadata
for Drizzle's query builder — they don't create database constraints. The `.references()`
calls on the columns do that.

## 5.4 The SQL Drizzle can't express

Some things need hand-written SQL. Create an empty migration and fill it in:

```bash
npx drizzle-kit generate --custom --name=search_and_indexes
```

```sql
-- enable fuzzy text matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- full-text search column, maintained by Postgres automatically
ALTER TABLE games ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(developer, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'C')
  ) STORED;

CREATE INDEX games_search_idx ON games USING GIN (search_vector);
CREATE INDEX games_title_trgm_idx ON games USING GIN (title gin_trgm_ops);

-- the Inbox query: assets with no game
CREATE INDEX assets_inbox_idx ON assets (capture_date DESC)
  WHERE game_id IS NULL;
```

What each piece does:

**`tsvector`** is Postgres's full-text search type. It stores words reduced to their stems
(*playing*, *played*, *plays* → *play*) so a search for "play" matches all of them.

**`GENERATED ALWAYS AS ... STORED`** means Postgres recomputes this column automatically
whenever title, developer or description changes. You never write to it and it can never get
out of sync.

**`setweight(..., 'A'|'B'|'C')`** ranks matches. A hit in the title outranks a hit in the
description, so searching "Zelda" surfaces the Zelda games rather than every game whose
description mentions Zelda.

**`pg_trgm`** breaks text into three-character sequences and compares overlap, which is what
lets `similarity('Elden Ring', 'elden rng') > 0.6` catch typos. That's the mechanism behind
Steam title matching.

**`GIN` indexes** are built for columns holding many values per row — words in a document,
trigrams in a string. Different structure from a normal B-tree index, right tool here.

**The partial index** (`WHERE game_id IS NULL`) only indexes unassigned assets. The Inbox
query stays instant no matter how large the archive grows, and the index stays tiny because it
only covers the handful of rows you care about.

---

# 6. Migrations and seed data

## 6.1 The migration runner

`db/migrate.ts`:

```ts
import { drizzle } from 'drizzle-orm/postgres-js'
import { migrate } from 'drizzle-orm/postgres-js/migrator'
import postgres from 'postgres'

const client = postgres(process.env.DATABASE_URL!, { max: 1 })

await migrate(drizzle(client), { migrationsFolder: './db/migrations' })
await client.end()

console.log('migrations complete')
```

`max: 1` — migrations must run serially on one connection. Running schema changes across a
pool can deadlock.

## 6.2 The workflow

Every single time you change `schema.ts`:

```bash
npm run db:generate          # writes db/migrations/0003_whatever.sql
cat db/migrations/0003_*.sql # READ IT before running it
npm run db:migrate           # applies it
git add db/migrations        # COMMIT IT
```

Reading the generated SQL is not optional. Drizzle occasionally infers a rename as a
drop-and-create, which would delete a column of real data. Sixty seconds of reading prevents
that.

Drizzle records applied migrations in a `__drizzle_migrations` table, so running `db:migrate`
twice is safe — the second run does nothing.

> **Never `drop database` as a workflow step.** It works fine now, when your data is fake.
> It's a catastrophe in month eight when it isn't, and the habit is what carries you there.
> Fix migrations forward.

## 6.3 `db/reset.ts`

For development only:

```ts
import postgres from 'postgres'

if (process.env.NODE_ENV === 'production') {
  throw new Error('reset is not allowed in production')
}

const client = postgres(process.env.DATABASE_URL!, { max: 1 })
await client`DROP SCHEMA public CASCADE`
await client`CREATE SCHEMA public`
await client.end()

console.log('database reset')
```

That guard on the first line is doing real work. Write it before you write the drop.

## 6.4 Seed data

Seed data exists to surface layout and query bugs before real data does. That means it must
include the ugly cases, not twenty tidy games.

`db/seed.ts`:

```ts
import sharp from 'sharp'
import { db } from './index'
import { games, artwork, assets, users } from './schema'
import { hashPassword } from '@/lib/auth'

const SEED = [
  { title: 'Elden Ring', status: 'playing', rating: 9.4, screenshots: 40 },
  { title: 'Hades', status: 'mastered', rating: 9.1, screenshots: 12 },

  // ---- the deliberately awkward ones ----
  { title: 'A Game With An Extremely Long Title That Will Absolutely Wrap Onto ' +
           'Several Lines In The Grid And Probably Break Something Somewhere',
    status: 'backlog', rating: null, screenshots: 0 },
  { title: 'Ünïcödé Tïtlé ゲーム 게임', status: 'completed',
    rating: 8.1, screenshots: 3 },
  { title: 'No Artwork At All', status: 'backlog',
    noArtwork: true, screenshots: 0 },
  { title: 'Zero Percent', status: 'playing',
    completion: 0, screenshots: 0 },
  { title: 'Hundred Percent', status: 'mastered',
    completion: 100, screenshots: 8 },
  { title: 'Screenshot Monster', status: 'completed', screenshots: 500 },
  { title: 'Broken Files', status: 'completed', brokenAssets: 3 },
  { title: 'Every Field Empty', minimal: true },
  { title: 'The Legend of Zelda', status: 'completed', rating: 9.6,
    screenshots: 20 },   // checks sortTitle handling
]
```

Why each awkward case earns its place:

| Case | Bug it catches |
|---|---|
| Very long title | Grid layout breaking, unbounded text overflow |
| Unicode | Encoding issues, broken sorting, mangled search |
| No artwork | Missing empty-state, broken `<img>` icon |
| 0% and 100% | Progress bars that render wrong at the extremes |
| 500 screenshots | Gallery performance, missing pagination |
| Broken files | Missing-file handling in the gallery and data health |
| Every field empty | Detail page assuming data exists |
| Leading "The" | Sort ordering |

Generate placeholder images rather than committing binaries:

```ts
async function placeholderCover(title: string, seed: number) {
  const hue = seed % 360
  return sharp({
    create: {
      width: 600, height: 900, channels: 3,
      background: { r: 30 + (hue % 40), g: 30, b: 50 + (hue % 60) },
    },
  }).png().toBuffer()
}
```

And seed the admin user:

```ts
await db.insert(users).values({
  username: process.env.ADMIN_USERNAME!,
  passwordHash: await hashPassword(process.env.ADMIN_PASSWORD!),
}).onConflictDoNothing()
```

`onConflictDoNothing` means re-running the seed doesn't fail on the existing user.

## 6.5 Verify

```bash
npm run db:reset
```

Then open TablePlus and check:

- Every table exists
- `games` holds your seed rows
- `SELECT title, sort_title FROM games` — does *The Legend of Zelda* sort correctly?
- Indexes exist: `\di` in psql, or the GUI's index panel
- `SELECT * FROM games WHERE search_vector @@ plainto_tsquery('english', 'zelda')`
  returns something

**Checkpoint for Part 1:** `docker compose -f compose.dev.yaml up` runs both containers,
`npm run db:reset` rebuilds a full database with awkward seed data, and you can browse it in a
GUI. Everyone on the team can do this.

That's the foundation. Part 2 builds the backend on top of it.
