# Build Manual — Part 2: Backend

*Auth, validation, the API layer, the list engine, and metadata providers.*

**The series:**
1. Foundations — concepts, setup, Docker, database
2. **Backend** ← you are here
3. Assets — storage, ingest, import, achievements, cards, jobs
4. Frontend & Operations — UI, search, testing, CI, deployment

---

# 7. Authentication

## 7.1 What a login actually is

There's no magic here, and understanding the pieces means you'll recognise when something is
wrong.

**Passwords are never stored.** You store a *hash* — a one-way fingerprint. When someone logs
in, you hash what they typed and compare fingerprints. If your database leaks, the attacker
gets hashes, not passwords.

**The hash must be deliberately slow.** SHA-256 (which we use for files) is fast by design —
a GPU computes billions per second, so a leaked SHA-256 password database is cracked in hours.
**bcrypt** is slow by design and tunable: a "cost factor" of 12 means roughly 4,000 rounds of
work, taking ~250ms. That's imperceptible to a person logging in and ruinous to someone trying
ten million guesses.

**bcrypt salts automatically.** A salt is random data mixed into each hash, so two users with
the same password get different hashes, and precomputed lookup tables are useless. bcrypt
stores the salt inside the hash string, so you don't manage it yourself.

**A session is a cookie.** After a successful login the server sets a cookie containing a
signed token. The browser sends it with every subsequent request. The server verifies the
signature and knows who you are. The signature is what `AUTH_SECRET` is for — without it,
anyone could forge a cookie claiming to be you.

The cookie needs three flags:

| Flag | Effect |
|---|---|
| `httpOnly` | JavaScript can't read it, so an XSS bug can't steal your session |
| `secure` | Only sent over HTTPS (skip in local development) |
| `sameSite: 'lax'` | Not sent on cross-site requests, which blocks CSRF attacks |

> **Do not hand-roll this.** Use a maintained auth library for session issuing and
> verification. The failure mode of getting it subtly wrong is silent — everything appears to
> work while your sessions are forgeable. This is the one place in the project where "I'll
> just write it myself" is genuinely dangerous.

## 7.2 Credential verification

`lib/auth.ts`:

```ts
import bcrypt from 'bcrypt'
import { db } from '@/db'
import { users } from '@/db/schema'
import { eq } from 'drizzle-orm'

const COST = 12

// a valid-format hash that matches nothing, used for timing safety
const DUMMY_HASH = '$2b$12$C6UzMDM.H6dfI/f/IKcEe.pu2Fr5vSg9K8dVYVv4dRUqRPO0Jo7Fq'

export async function hashPassword(password: string) {
  return bcrypt.hash(password, COST)
}

export async function verifyCredentials(username: string, password: string) {
  const user = await db.query.users.findFirst({
    where: eq(users.username, username),
  })

  if (!user) {
    // Compare anyway so a missing user takes the same time as a wrong password.
    // Otherwise response timing reveals which usernames exist.
    await bcrypt.compare(password, DUMMY_HASH)
    return null
  }

  const ok = await bcrypt.compare(password, user.passwordHash)
  return ok ? { id: user.id, username: user.username } : null
}
```

That dummy comparison is a **timing attack** defence. If a missing user returned instantly and
a wrong password took 250ms, an attacker could enumerate valid usernames by measuring response
times. Doing the same work either way removes the signal.

## 7.3 Rate limiting

Even with slow hashing, unlimited attempts are unlimited attempts.

`lib/rate-limit.ts`:

```ts
type Bucket = { count: number; resetAt: number }
const buckets = new Map<string, Bucket>()

export function checkRateLimit(key: string, limit = 5, windowMs = 15 * 60_000) {
  const now = Date.now()
  const bucket = buckets.get(key)

  if (!bucket || now > bucket.resetAt) {
    buckets.set(key, { count: 1, resetAt: now + windowMs })
    return { allowed: true, remaining: limit - 1 }
  }

  if (bucket.count >= limit) {
    return { allowed: false, retryAfterMs: bucket.resetAt - now }
  }

  bucket.count++
  return { allowed: true, remaining: limit - bucket.count }
}

// stop the map growing forever
setInterval(() => {
  const now = Date.now()
  for (const [k, v] of buckets) if (now > v.resetAt) buckets.delete(k)
}, 60_000).unref()
```

In-memory is fine here: single user, single server instance. It resets on restart, which
matters not at all for a home server. `.unref()` stops that interval keeping the Node process
alive during shutdown.

## 7.4 The login route

```ts
// app/api/auth/login/route.ts
import { NextResponse } from 'next/server'
import { z } from 'zod'
import { verifyCredentials } from '@/lib/auth'
import { checkRateLimit } from '@/lib/rate-limit'
import { createSession } from '@/lib/session'

const schema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
})

export async function POST(req: Request) {
  const ip = req.headers.get('x-forwarded-for') ?? 'local'
  const limit = checkRateLimit(`login:${ip}`)

  if (!limit.allowed) {
    return NextResponse.json(
      { error: { code: 'rate_limited', message: 'Too many attempts. Try again later.' } },
      { status: 429, headers: { 'Retry-After': String(Math.ceil(limit.retryAfterMs! / 1000)) } },
    )
  }

  const body = schema.safeParse(await req.json())
  if (!body.success) {
    return NextResponse.json(
      { error: { code: 'invalid', message: 'Username and password required' } },
      { status: 400 },
    )
  }

  const user = await verifyCredentials(body.data.username, body.data.password)
  if (!user) {
    // deliberately vague — never say which half was wrong
    return NextResponse.json(
      { error: { code: 'invalid_credentials', message: 'Incorrect username or password' } },
      { status: 401 },
    )
  }

  await createSession(user)
  return NextResponse.json({ user })
}
```

"Incorrect username or password" rather than "no such user" is deliberate: don't confirm which
usernames exist.

## 7.5 Middleware

Middleware runs before every request. It's where you enforce "logged in or go away" once,
rather than remembering to check in fifty route handlers.

`middleware.ts` at the repo root:

```ts
import { NextResponse, type NextRequest } from 'next/server'
import { getSession } from '@/lib/session'

const PUBLIC = ['/login', '/api/auth/login', '/api/health']

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl

  if (PUBLIC.some((p) => pathname.startsWith(p))) {
    return NextResponse.next()
  }

  const session = await getSession(req)

  if (!session) {
    // API callers want a status code; browsers want a redirect
    if (pathname.startsWith('/api')) {
      return NextResponse.json(
        { error: { code: 'unauthorized', message: 'Not signed in' } },
        { status: 401 },
      )
    }
    const url = new URL('/login', req.url)
    url.searchParams.set('next', pathname)   // return here after login
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
```

That `matcher` regex is a negative lookahead: run on everything *except* static assets. Running
middleware on every image request would be pure waste.

**Allowlist, never blocklist.** `PUBLIC` names the handful of routes that don't need a session.
Everything else is protected by default. A blocklist means the day you add a route and forget
to protect it, it's open.

**Checkpoint:** log out, then try `/games`, `/api/games`, and `/settings`. The pages redirect;
the API returns 401. Now log in and confirm all three work.

---

# 8. The validation layer

## 8.1 Why runtime validation exists

TypeScript checks types when you compile. It's gone when the code runs. So this:

```ts
const body = await req.json() as GameCreate   // a lie
```

is a lie you're telling the compiler. The request body could be anything — `null`, a string, an
object with a 40MB title, a missing required field. TypeScript believes you and the crash
happens three functions later, somewhere confusing.

Zod checks the actual data:

```ts
const body = gameCreateSchema.parse(await req.json())  // throws if wrong
```

Now `body` really is the shape you claimed, or you got a clear error at the boundary.

The bigger win: **one schema, two consumers.** The API route validates with it, and the form
validates with it. They cannot drift apart, because there's only one definition.

## 8.2 `lib/zod/game.ts`

```ts
import { z } from 'zod'

export const gameStatusSchema = z.enum([
  'wishlist', 'backlog', 'playing', 'paused',
  'completed', 'mastered', 'dropped',
])

const ratingValue = z.coerce.number().min(0).max(10).nullable()

export const gameCreateSchema = z.object({
  title: z.string().trim().min(1, 'Title is required').max(500),
  sortTitle: z.string().max(500).optional(),
  description: z.string().max(20_000).nullable().optional(),
  releaseDate: z.string().date().nullable().optional(),
  developer: z.string().max(200).nullable().optional(),
  publisher: z.string().max(200).nullable().optional(),
  status: gameStatusSchema.default('backlog'),
  priority: z.enum(['low', 'normal', 'high']).nullable().optional(),
  favorite: z.boolean().default(false),
  notes: z.string().max(100_000).nullable().optional(),
  resumeNote: z.string().max(2_000).nullable().optional(),
  genres: z.array(z.string().trim().min(1)).max(20).default([]),
  tags: z.array(z.string().trim().min(1)).max(50).default([]),
})

export const gameUpdateSchema = gameCreateSchema.partial()

export type GameCreate = z.infer<typeof gameCreateSchema>
export type GameUpdate = z.infer<typeof gameUpdateSchema>
```

Details that matter:

**`z.coerce.number()`** — HTML form inputs and URL query strings are always strings. `"9.4"`
becomes `9.4` rather than failing. Without coercion every query param needs manual conversion.

**Explicit `.max()` on every string.** Not pedantry — an unbounded text field is a way to fill
your disk with one request. Pick generous but finite limits.

**`.partial()`** turns every field optional in one call, which is exactly what a PATCH needs.
Defining the update schema separately would guarantee they drift.

**`z.infer<>`** derives the TypeScript type from the schema. The type and the validation can
never disagree, because one generates the other.

## 8.3 The query schema

```ts
export const gameQuerySchema = z.object({
  status: gameStatusSchema.optional(),
  platform: z.string().optional(),
  genre: z.string().optional(),
  tag: z.string().optional(),
  favorite: z.coerce.boolean().optional(),
  q: z.string().trim().min(1).max(200).optional(),
  sort: z.enum(['title', 'rating', 'release', 'added', 'playtime', 'rank'])
    .default('title'),
  order: z.enum(['asc', 'desc']).default('asc'),
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(200).default(60),
})

export type GameQuery = z.infer<typeof gameQuerySchema>
```

**`sort` is an enum, not a string.** This is a security boundary. If you accepted an arbitrary
string and interpolated it into SQL, you'd have an injection hole. An enum means only six
values ever reach the query builder, and the mapping to columns is a lookup table you control.

**`limit` is capped at 200.** Without the cap, `?limit=999999999` is a denial-of-service in a
URL.

## 8.4 Computing the overall rating

`lib/rating.ts`:

```ts
export const RATING_WEIGHTS = {
  story: 0.2,
  gameplay: 0.2,
  soundtrack: 0.2,
  presentation: 0.2,
  enjoyment: 0.2,
} as const

export type RatingAxis = keyof typeof RATING_WEIGHTS
export type RatingInput = Partial<Record<RatingAxis, number | null>>

export function computeOverall(r: RatingInput): number | null {
  const rated = (Object.keys(RATING_WEIGHTS) as RatingAxis[])
    .filter((axis) => r[axis] != null)

  if (rated.length === 0) return null

  const totalWeight = rated.reduce((sum, a) => sum + RATING_WEIGHTS[a], 0)
  const weighted = rated.reduce((sum, a) => sum + r[a]! * RATING_WEIGHTS[a], 0)

  return Number((weighted / totalWeight).toFixed(2))
}
```

The important behaviour is the **re-normalisation**. Divide by the weight of the axes actually
rated, not by 1.0. Rate a game 9.0 on gameplay only, and you get 9.0 — not 1.8. Without this,
partially rated games look terrible.

Stored at two decimal places, displayed at one. That way `9.26` and `9.34` both show as
"9.3" but sort correctly against each other.

---

# 9. The API layer

## 9.1 Error handling, once

Every route needs the same error handling. Write it once.

`lib/api.ts`:

```ts
import { NextResponse } from 'next/server'
import { ZodError, type ZodSchema } from 'zod'

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status = 400,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export function ok<T>(data: T, status = 200) {
  return NextResponse.json(data, { status })
}

export function handle(fn: () => Promise<Response>) {
  return fn().catch((err) => {
    if (err instanceof ZodError) {
      return NextResponse.json({
        error: {
          code: 'validation',
          message: 'Some fields are invalid',
          issues: err.issues.map((i) => ({
            field: i.path.join('.'),
            message: i.message,
          })),
        },
      }, { status: 422 })
    }

    if (err instanceof ApiError) {
      return NextResponse.json(
        { error: { code: err.code, message: err.message } },
        { status: err.status },
      )
    }

    // unexpected: log the detail, tell the user nothing
    console.error('[api] unhandled', err)
    return NextResponse.json(
      { error: { code: 'internal', message: 'Something went wrong' } },
      { status: 500 },
    )
  })
}

export function parseQuery<T>(req: Request, schema: ZodSchema<T>): T {
  const params = Object.fromEntries(new URL(req.url).searchParams)
  return schema.parse(params)
}
```

Three tiers, deliberately:

**Zod errors → 422** with per-field detail, so the form can highlight the exact input that's
wrong.

**`ApiError` → your chosen status.** These are expected failures — not found, too large,
unsupported type — and the message is safe to show the user.

**Everything else → 500**, logged in full server-side, opaque to the client. Never leak a
stack trace or a database error message to the browser; those tell an attacker about your
schema.

### Status codes worth knowing

| Code | Meaning | Use |
|---|---|---|
| 200 | OK | Successful GET/PATCH |
| 201 | Created | Successful POST that made something |
| 400 | Bad request | Malformed |
| 401 | Unauthorized | Not logged in |
| 403 | Forbidden | Logged in, not allowed |
| 404 | Not found | |
| 409 | Conflict | Duplicate that isn't allowed |
| 413 | Payload too large | Oversized upload |
| 415 | Unsupported media type | Wrong file type |
| 422 | Unprocessable | Valid JSON, invalid values |
| 429 | Too many requests | Rate limited |
| 500 | Server error | Your bug |

## 9.2 The route shape

Every route in the app looks like this:

```ts
// app/api/games/route.ts
import { handle, ok, parseQuery } from '@/lib/api'
import { requireSession } from '@/lib/session'
import { gameQuerySchema, gameCreateSchema } from '@/lib/zod/game'
import { listGames, createGame } from '@/features/games'

export async function GET(req: Request) {
  return handle(async () => {
    await requireSession()
    const query = parseQuery(req, gameQuerySchema)
    return ok(await listGames(query))
  })
}

export async function POST(req: Request) {
  return handle(async () => {
    const session = await requireSession()
    const body = gameCreateSchema.parse(await req.json())
    const game = await createGame(session.userId, body)
    return ok(game, 201)
  })
}
```

Note the shape: **routes do four things** — check the session, validate input, call a feature
function, return. No business logic in routes. Logic lives in `features/`, which means it's
testable without an HTTP request and reusable from a background job.

Dynamic routes take params:

```ts
// app/api/games/[id]/route.ts
export async function GET(_req: Request, { params }: { params: { id: string } }) {
  return handle(async () => {
    await requireSession()
    const game = await getGame(params.id)
    if (!game) throw new ApiError('not_found', 'Game not found', 404)
    return ok(game)
  })
}
```

## 9.3 The list engine

This is the piece that makes every library view cheap to build. One function, driven by the
parsed query.

`features/games/query.ts`:

```ts
import { and, asc, desc, eq, sql, type SQL } from 'drizzle-orm'
import { db } from '@/db'
import { games, gameGenres, genres, gameTags, tags, gamePlatforms } from '@/db/schema'
import type { GameQuery } from '@/lib/zod/game'

// The only columns anyone can sort by. The enum in the schema guarantees
// the key exists, so nothing user-supplied reaches SQL.
const SORT_COLUMNS = {
  title:   games.sortTitle,
  rating:  games.ratingOverall,
  release: games.releaseDate,
  added:   games.createdAt,
  rank:    games.personalRank,
} as const

export async function listGames(q: GameQuery) {
  const conditions: SQL[] = []

  if (q.status)   conditions.push(eq(games.status, q.status))
  if (q.favorite) conditions.push(eq(games.favorite, true))

  // full-text search, with a trigram fallback for typos
  if (q.q) {
    conditions.push(sql`(
      ${games.searchVector} @@ plainto_tsquery('english', ${q.q})
      OR ${games.title} % ${q.q}
    )`)
  }

  // EXISTS subqueries for the many-to-many filters
  if (q.genre) {
    conditions.push(sql`EXISTS (
      SELECT 1 FROM ${gameGenres}
      JOIN ${genres} ON ${genres.id} = ${gameGenres.genreId}
      WHERE ${gameGenres.gameId} = ${games.id}
        AND ${genres.slug} = ${q.genre}
    )`)
  }

  if (q.tag) {
    conditions.push(sql`EXISTS (
      SELECT 1 FROM ${gameTags}
      JOIN ${tags} ON ${tags.id} = ${gameTags.tagId}
      WHERE ${gameTags.gameId} = ${games.id}
        AND ${tags.slug} = ${q.tag}
    )`)
  }

  if (q.platform) {
    conditions.push(sql`EXISTS (
      SELECT 1 FROM ${gamePlatforms}
      WHERE ${gamePlatforms.gameId} = ${games.id}
        AND ${gamePlatforms.platform} = ${q.platform}
    )`)
  }

  const where = conditions.length ? and(...conditions) : undefined
  const direction = q.order === 'desc' ? desc : asc

  const orderBy = q.sort === 'playtime'
    ? direction(sql`(
        SELECT COALESCE(SUM(playtime_minutes), 0)
        FROM game_platforms WHERE game_id = ${games.id}
      )`)
    : direction(SORT_COLUMNS[q.sort as keyof typeof SORT_COLUMNS])

  const [rows, [{ count }]] = await Promise.all([
    db.select()
      .from(games)
      .where(where)
      .orderBy(orderBy, asc(games.id))          // ← stable tiebreak
      .limit(q.limit)
      .offset((q.page - 1) * q.limit),

    db.select({ count: sql<number>`count(*)::int` })
      .from(games)
      .where(where),
  ])

  return {
    rows,
    count,
    page: q.page,
    limit: q.limit,
    pages: Math.ceil(count / q.limit),
  }
}
```

### Things worth understanding here

**Why `EXISTS` and not `JOIN`.** Joining a game to its genres produces one row per genre — a
game with four genres appears four times, and your pagination is wrong. `EXISTS` asks a
yes/no question without multiplying rows. You'd otherwise need `DISTINCT`, which is slower and
interacts badly with `ORDER BY`.

**Why parameters, not string concatenation.** Drizzle's `sql` template turns `${q.q}` into a
bound parameter, sent separately from the query text. The database never parses user input as
SQL. Building the string yourself with `+` is how SQL injection happens. Never do it.

**Why the `asc(games.id)` tiebreak is not optional.** Sorting by `rating` when forty games are
unrated means forty rows with equal sort keys. Postgres makes no guarantee about their relative
order between queries — page 1 and page 2 can overlap or skip. Adding a unique tiebreak makes
the ordering total and deterministic. **This bug is subtle, intermittent, and takes a weekend to
find.** One line prevents it.

**Why the count runs in parallel.** `Promise.all` issues both queries at once instead of
waiting for the first. Roughly halves the latency of every library page load.

**`::int`** casts the count — Postgres returns `count(*)` as `bigint`, which arrives as a
string in JavaScript because bigints exceed `Number.MAX_SAFE_INTEGER`. Casting avoids
`"1284"` where you expected `1284`.

**`OFFSET` and large pages.** `OFFSET 100000` makes Postgres scan and discard 100,000 rows.
Fine at your scale — a few thousand games — and if you ever notice it, the fix is
keyset pagination (`WHERE (sort_title, id) > (:last_title, :last_id)`).

## 9.4 Creating a game

`features/games/create.ts`:

```ts
import { db } from '@/db'
import { games, genres, gameGenres, timelineEvents, fieldOrigins } from '@/db/schema'
import type { GameCreate } from '@/lib/zod/game'
import { eq } from 'drizzle-orm'
import { slugify } from '@/lib/utils'

/** "The Legend of Zelda" → "Legend of Zelda, The" */
export function makeSortTitle(title: string) {
  const m = title.match(/^(a|an|the)\s+(.+)$/i)
  return m ? `${m[2]}, ${m[1]}` : title
}

export async function createGame(userId: string, input: GameCreate) {
  return db.transaction(async (tx) => {
    const [game] = await tx.insert(games).values({
      title: input.title,
      sortTitle: input.sortTitle ?? makeSortTitle(input.title),
      description: input.description ?? null,
      releaseDate: input.releaseDate ?? null,
      developer: input.developer ?? null,
      publisher: input.publisher ?? null,
      status: input.status,
      priority: input.priority ?? null,
      favorite: input.favorite,
      notes: input.notes ?? null,
      resumeNote: input.resumeNote ?? null,
    }).returning()

    await attachGenres(tx, game.id, input.genres)
    await attachTags(tx, game.id, input.tags)

    // manual creation means every field is yours, not a provider's
    const provided = Object.keys(input).filter(
      (k) => PROVIDER_FIELDS.includes(k as any),
    )
    if (provided.length) {
      await tx.insert(fieldOrigins).values(
        provided.map((fieldName) => ({
          gameId: game.id, fieldName, source: 'custom' as const,
        })),
      )
    }

    await tx.insert(timelineEvents).values({
      userId,
      type: 'game_added',
      gameId: game.id,
      occurredAt: new Date(),
    })

    return game
  })
}
```

**Everything is in one transaction.** If the timeline insert fails, the game insert rolls back
too. You never end up with a game that has no creation event, or genres attached to a game that
doesn't exist.

**`tx` replaces `db` inside the callback.** Using `db` there would run outside the transaction
— a classic and invisible bug. If a statement inside a transaction block uses `db`, it isn't
protected.

Attaching tags, with get-or-create:

```ts
async function attachTags(tx: any, gameId: string, names: string[]) {
  for (const name of names) {
    const slug = slugify(name)

    const [tag] = await tx.insert(tags)
      .values({ name, slug })
      .onConflictDoUpdate({ target: tags.slug, set: { name } })
      .returning()

    await tx.insert(gameTags)
      .values({ gameId, tagId: tag.id })
      .onConflictDoNothing()
  }
}
```

`onConflictDoUpdate` is an **upsert** — insert, or update if it already exists. The alternative
(select, then insert if missing) has a race condition: two requests can both find nothing and
both insert. The database-level upsert is atomic and correct.

## 9.5 Updating, and marking fields custom

```ts
// features/games/update.ts
export const PROVIDER_FIELDS = [
  'title', 'altTitles', 'description', 'releaseDate', 'developer', 'publisher',
] as const

export async function updateGame(gameId: string, patch: GameUpdate) {
  return db.transaction(async (tx) => {
    if (patch.title && !patch.sortTitle) {
      patch.sortTitle = makeSortTitle(patch.title)
    }

    const [game] = await tx.update(games)
      .set({ ...patch, updatedAt: new Date() })
      .where(eq(games.id, gameId))
      .returning()

    // any provider-owned field you edit becomes yours
    for (const field of Object.keys(patch)) {
      if (!PROVIDER_FIELDS.includes(field as any)) continue

      await tx.insert(fieldOrigins)
        .values({ gameId, fieldName: field, source: 'custom' })
        .onConflictDoUpdate({
          target: [fieldOrigins.gameId, fieldOrigins.fieldName],
          set: { source: 'custom', provider: null, updatedAt: new Date() },
        })
    }

    return game
  })
}
```

This is one half of the anti-clobber mechanism. §11 is the other half.

Note that personal fields — rating, status, notes, favourite — get no origin row at all. They
were never a provider's to overwrite, so they don't need protecting; the merge simply never
touches them.

## 9.6 Rating updates with history

```ts
export async function updateRating(gameId: string, input: RatingInput) {
  return db.transaction(async (tx) => {
    const before = await tx.query.games.findFirst({ where: eq(games.id, gameId) })
    if (!before) throw new ApiError('not_found', 'Game not found', 404)

    const overall = computeOverall(input)

    const [game] = await tx.update(games).set({
      ratingStory: input.story?.toString() ?? null,
      ratingGameplay: input.gameplay?.toString() ?? null,
      ratingSoundtrack: input.soundtrack?.toString() ?? null,
      ratingPresentation: input.presentation?.toString() ?? null,
      ratingEnjoyment: input.enjoyment?.toString() ?? null,
      ratingOverall: overall?.toString() ?? null,
      ratingConfidence: input.confidence ?? null,
      updatedAt: new Date(),
    }).where(eq(games.id, gameId)).returning()

    // record only the axes that actually moved
    for (const axis of ['story','gameplay','soundtrack','presentation','enjoyment'] as const) {
      const col = `rating${axis[0].toUpperCase()}${axis.slice(1)}` as keyof typeof before
      const oldValue = before[col] ? Number(before[col]) : null
      const newValue = input[axis] ?? null
      if (oldValue === newValue) continue

      await tx.insert(ratingHistory).values({
        gameId, axis, oldValue: oldValue?.toString() ?? null,
        newValue: newValue?.toString() ?? null, changedAt: new Date(),
      })
    }

    if (before.ratingOverall !== overall?.toString()) {
      await tx.insert(timelineEvents).values({
        userId: SYSTEM_USER_ID, type: 'rating_changed', gameId,
        metadata: { from: before.ratingOverall, to: overall },
        occurredAt: new Date(),
      })
    }

    return game
  })
}
```

**`.toString()` on numerics.** Drizzle returns and accepts `numeric` columns as strings, to
avoid the floating-point precision loss that would defeat the point of using `numeric`.
Convert with `Number()` for arithmetic, back to string for storage.

**Only log axes that changed.** Otherwise every save writes five history rows and the history
becomes noise.

---

# 10. Metadata providers

## 10.1 The interface

The point of an interface is that nothing else in the app knows a provider's name. Add TMDB in
two years and no calling code changes.

`features/metadata/providers/base.ts`:

```ts
export interface SearchResult {
  externalId: string
  title: string
  year?: number
  coverUrl?: string
  summary?: string
}

export interface ProviderArtwork {
  kind: 'cover' | 'background' | 'logo'
  url: string
}

export interface ProviderDetails {
  title: string
  altTitles: string[]
  description?: string
  releaseDate?: string          // ISO yyyy-mm-dd
  developer?: string
  publisher?: string
  genres: string[]
  franchise?: string
  platforms: string[]
  artwork: ProviderArtwork[]
  externalIds: Record<string, string>
}

export interface MetadataProvider {
  id: 'igdb' | 'steam'
  search(query: string): Promise<SearchResult[]>
  getDetails(externalId: string): Promise<ProviderDetails>
}
```

**Normalisation is the whole job.** IGDB returns release dates as Unix timestamps, nests
developer inside `involved_companies[].company.name`, and gives artwork as image IDs you build
URLs from. None of that leaks past the provider file. Everything downstream sees
`ProviderDetails`.

## 10.2 The cached, rate-limited client

Nothing calls `fetch` directly. Everything goes through this.

`features/metadata/client.ts`:

```ts
import { createHash } from 'node:crypto'
import { db } from '@/db'
import { providerCache } from '@/db/schema'
import { and, eq } from 'drizzle-orm'

// one promise chain per provider = requests are serialised with a gap
const chains = new Map<string, Promise<void>>()

async function throttle(provider: string, minGapMs: number) {
  const previous = chains.get(provider) ?? Promise.resolve()

  let release!: () => void
  const current = new Promise<void>((resolve) => { release = resolve })
  chains.set(provider, previous.then(() => current))

  await previous                      // wait my turn
  setTimeout(release, minGapMs)       // hold the slot for the gap
}

export async function cachedFetch<T>(opts: {
  provider: string
  endpoint: string
  params: unknown
  minGapMs?: number
  ttlMs?: number                      // omit = cache forever
  fetcher: () => Promise<T>
}): Promise<T> {
  const paramsHash = createHash('sha256')
    .update(JSON.stringify(opts.params))
    .digest('hex')

  const cached = await db.query.providerCache.findFirst({
    where: and(
      eq(providerCache.provider, opts.provider),
      eq(providerCache.endpoint, opts.endpoint),
      eq(providerCache.paramsHash, paramsHash),
    ),
  })

  if (cached) {
    const age = Date.now() - cached.fetchedAt.getTime()
    if (!opts.ttlMs || age < opts.ttlMs) {
      return cached.response as T
    }
  }

  await throttle(opts.provider, opts.minGapMs ?? 250)

  let response: T
  try {
    response = await opts.fetcher()
  } catch (err) {
    // network died but we hold a stale copy — better than nothing
    if (cached) {
      console.warn(`[${opts.provider}] fetch failed, serving stale cache`)
      return cached.response as T
    }
    throw err
  }

  await db.insert(providerCache)
    .values({
      provider: opts.provider, endpoint: opts.endpoint,
      paramsHash, response, fetchedAt: new Date(),
    })
    .onConflictDoUpdate({
      target: [providerCache.provider, providerCache.endpoint,
               providerCache.paramsHash],
      set: { response, fetchedAt: new Date() },
    })

  return response as T
}
```

### How the throttle works

Each provider gets a chain of promises. A new request appends itself, waits for everything
before it, then holds its slot open for `minGapMs`. Requests come out spaced by at least that
gap, no matter how many arrive at once.

That's what keeps you under IGDB's four-requests-per-second limit while importing.

### Cache policy

**Game details: no TTL, cached forever.** Game facts don't change, and if IGDB disappears
tomorrow you keep everything it ever told you. This is principle 1 made concrete.

**Search results: a TTL** — new games get added, so a stale search misses them.

**Stale-on-error.** If the network fails and you hold an expired copy, serve it with a warning
rather than erroring. The archive keeps working.

**The development benefit is enormous.** Building the import UI means running the same search
fifty times. With this cache, forty-nine of them never leave your machine.

## 10.3 IGDB

Two unusual things about IGDB: authentication goes through Twitch, and queries are written in
a small text language called apicalypse, sent as the POST body.

```ts
// features/metadata/providers/igdb.ts
import { cachedFetch } from '../client'
import type { MetadataProvider, ProviderDetails, SearchResult } from './base'

const API = 'https://api.igdb.com/v4'

let token: { value: string; expiresAt: number } | null = null

async function getToken(): Promise<string> {
  if (token && Date.now() < token.expiresAt - 60_000) return token.value

  const url = new URL('https://id.twitch.tv/oauth2/token')
  url.searchParams.set('client_id', process.env.IGDB_CLIENT_ID!)
  url.searchParams.set('client_secret', process.env.IGDB_CLIENT_SECRET!)
  url.searchParams.set('grant_type', 'client_credentials')

  const res = await fetch(url, { method: 'POST' })
  if (!res.ok) throw new Error(`IGDB auth failed: ${res.status}`)

  const json = await res.json()
  token = {
    value: json.access_token,
    expiresAt: Date.now() + json.expires_in * 1000,
  }
  return token.value
}
```

**`client_credentials`** is the OAuth flow for machine-to-machine access — no user consent,
just your app proving who it is. The token lasts weeks; we cache it in memory and refresh a
minute before expiry.

**In-memory is deliberate.** Losing it on restart costs one extra request.

```ts
async function query<T>(endpoint: string, body: string): Promise<T> {
  const run = async (): Promise<T> => {
    const res = await fetch(`${API}/${endpoint}`, {
      method: 'POST',
      headers: {
        'Client-ID': process.env.IGDB_CLIENT_ID!,
        Authorization: `Bearer ${await getToken()}`,
        Accept: 'application/json',
      },
      body,
    })

    if (res.status === 401) { token = null; throw new Error('igdb-401') }
    if (res.status === 429) throw new Error('igdb-429')
    if (!res.ok) throw new Error(`IGDB ${endpoint}: ${res.status}`)
    return res.json()
  }

  return cachedFetch({
    provider: 'igdb',
    endpoint,
    params: body,
    minGapMs: 260,                    // ~4 req/sec
    fetcher: async () => {
      try {
        return await run()
      } catch (err) {
        if (err instanceof Error && /igdb-(401|429)/.test(err.message)) {
          await new Promise((r) => setTimeout(r, 1200))
          return run()                // one retry, after clearing the token
        }
        throw err
      }
    },
  })
}
```

**On 401 we null the token then retry** — that's the self-healing path for an expired token.
**On 429 we wait and retry once**, which covers a brief burst. More than one retry would mask a
genuine problem.

```ts
const img = (imageId: string, size: string) =>
  `https://images.igdb.com/igdb/image/upload/t_${size}/${imageId}.jpg`

export const igdb: MetadataProvider = {
  id: 'igdb',

  async search(q: string): Promise<SearchResult[]> {
    const safe = q.replace(/["\\]/g, '')     // apicalypse strings are quoted

    const rows = await query<any[]>('games', `
      search "${safe}";
      fields name, first_release_date, summary, cover.image_id;
      limit 20;
    `)

    return rows.map((r) => ({
      externalId: String(r.id),
      title: r.name,
      year: r.first_release_date
        ? new Date(r.first_release_date * 1000).getFullYear()
        : undefined,
      coverUrl: r.cover?.image_id ? img(r.cover.image_id, 'cover_big') : undefined,
      summary: r.summary,
    }))
  },

  async getDetails(id: string): Promise<ProviderDetails> {
    const [r] = await query<any[]>('games', `
      fields name, alternative_names.name, summary, storyline,
             first_release_date, genres.name, franchises.name,
             platforms.name, cover.image_id, artworks.image_id,
             involved_companies.company.name,
             involved_companies.developer,
             involved_companies.publisher;
      where id = ${Number(id)};
    `)

    if (!r) throw new Error(`IGDB game ${id} not found`)

    const companies = r.involved_companies ?? []
    const artwork: ProviderDetails['artwork'] = []
    if (r.cover?.image_id) {
      artwork.push({ kind: 'cover', url: img(r.cover.image_id, '1080p') })
    }
    if (r.artworks?.[0]?.image_id) {
      artwork.push({ kind: 'background', url: img(r.artworks[0].image_id, '1080p') })
    }

    return {
      title: r.name,
      altTitles: (r.alternative_names ?? []).map((a: any) => a.name),
      description: r.summary ?? r.storyline,
      releaseDate: r.first_release_date
        ? new Date(r.first_release_date * 1000).toISOString().slice(0, 10)
        : undefined,
      developer: companies.find((c: any) => c.developer)?.company?.name,
      publisher: companies.find((c: any) => c.publisher)?.company?.name,
      genres: (r.genres ?? []).map((g: any) => g.name),
      franchise: r.franchises?.[0]?.name,
      platforms: (r.platforms ?? []).map((p: any) => p.name),
      artwork,
      externalIds: { igdb: String(r.id) },
    }
  },
}
```

**`Number(id)` in the where clause** is not cosmetic — it's the injection guard for that
interpolation. A non-numeric id becomes `NaN` and the query fails safely rather than smuggling
in apicalypse syntax.

**`?.` and `?? []` everywhere.** IGDB omits fields it has no data for; it doesn't return
nulls. Assuming a field exists is the fastest way to crash on an obscure game.

**Verify the image size slugs** (`cover_big`, `1080p`) against IGDB's current docs when you
build this — they occasionally add or rename sizes.

## 10.4 Steam

Steam doesn't search; it enumerates your library. Different shape, same interface family.

```ts
// features/metadata/providers/steam.ts
export async function fetchOwnedGames() {
  const url = new URL(
    'https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/')
  url.searchParams.set('key', process.env.STEAM_API_KEY!)
  url.searchParams.set('steamid', process.env.STEAM_ID64!)
  url.searchParams.set('include_appinfo', '1')
  url.searchParams.set('include_played_free_games', '1')

  const json = await cachedFetch<any>({
    provider: 'steam',
    endpoint: 'owned-games',
    params: { steamId: process.env.STEAM_ID64 },
    ttlMs: 60 * 60 * 1000,               // an hour
    fetcher: async () => {
      const res = await fetch(url)
      if (!res.ok) throw new Error(`Steam API ${res.status}`)
      return res.json()
    },
  })

  const list = json.response?.games
  if (!list) {
    throw new Error(
      'Steam returned no games. Is your profile and game list set to public?')
  }

  return list.map((g: any) => ({
    appId: String(g.appid),
    name: g.name as string,
    playtimeMinutes: g.playtime_forever as number,
  }))
}
```

That explicit error message is worth writing. A private Steam profile returns an empty success
response, not an error, and everyone hits it once.

### The sync, with a review step

```ts
// features/metadata/steam-sync.ts
export async function syncSteamLibrary() {
  const owned = await fetchOwnedGames()
  const matched: { gameId: string; playtimeMinutes: number }[] = []
  const review: UnmatchedGame[] = []

  for (const g of owned) {
    // 1. exact match on a stored Steam appid
    const existing = await db.query.externalIds.findFirst({
      where: and(
        eq(externalIds.provider, 'steam'),
        eq(externalIds.externalId, g.appId),
      ),
    })

    if (existing) {
      matched.push({ gameId: existing.gameId, playtimeMinutes: g.playtimeMinutes })
      continue
    }

    // 2. fuzzy title match — a SUGGESTION, never an assumption
    const rows = await db.execute<{ id: string; title: string; score: number }>(sql`
      SELECT id, title, similarity(title, ${g.name}) AS score
      FROM games
      WHERE similarity(title, ${g.name}) > 0.6
      ORDER BY score DESC
      LIMIT 1
    `)

    review.push({ ...g, suggestion: rows[0] ?? null })
  }

  for (const m of matched) await upsertSteamPlaytime(m)

  return { matched: matched.length, review }
}
```

> **Never auto-create from a fuzzy match.** Trigram similarity will confuse *Portal* with
> *Portal 2*, and *Batman: Arkham City* with *Batman: Arkham City GOTY*. A wrongly created
> game is worse than no game — you'll find it months later with screenshots attached to the
> wrong entry. The review list costs the user thirty seconds and prevents that permanently.

Accepting a review item creates the game, writes its Steam `external_id`, and queues an IGDB
lookup for real metadata and artwork. Steam gives you ownership and playtime; IGDB gives you
everything else.

```ts
async function upsertSteamPlaytime(m: { gameId: string; playtimeMinutes: number }) {
  await db.insert(gamePlatforms)
    .values({
      gameId: m.gameId,
      platform: 'Steam',
      playtimeMinutes: m.playtimeMinutes,
    })
    .onConflictDoUpdate({
      target: [gamePlatforms.gameId, gamePlatforms.platform],
      set: { playtimeMinutes: m.playtimeMinutes, updatedAt: new Date() },
    })
}
```

---

# 11. Field origin and safe refresh

This is the mechanism behind principle 1. It deserves its own section because it's the promise
the entire archive rests on, and because it's easy to break silently.

## 11.1 The problem

Import Elden Ring from IGDB. Rewrite the description in your own words. Six months later, hit
"Refresh Metadata" to pick up new artwork.

Without this mechanism, your description is gone. You wouldn't notice for weeks, and there'd be
no way back.

## 11.2 The mechanism

Three categories of field:

| Category | Examples | Sync behaviour |
|---|---|---|
| **Provider-owned** | title, description, release date, developer, publisher | Updated on refresh — *unless* you edited it |
| **Personal** | rating, status, notes, favourite, rank, resume note | Never touched. Not even considered |
| **Assets** | screenshots, clips, albums | Never touched |

Only the first category needs tracking. `field_origins` holds one row per game per
provider-owned field, saying `provider` or `custom`.

```
game: Elden Ring
  title        → provider (igdb)
  description  → custom          ← you edited this
  releaseDate  → provider (igdb)
  developer    → provider (igdb)
```

## 11.3 The merge

`features/metadata/merge.ts`:

```ts
import { db } from '@/db'
import { games, fieldOrigins } from '@/db/schema'
import { eq } from 'drizzle-orm'
import type { ProviderDetails } from './providers/base'

/**
 * The ONLY fields a provider may ever write.
 * Adding to this list means giving a provider power over that field —
 * think before you do it.
 */
export const PROVIDER_FIELDS = [
  'title', 'altTitles', 'description',
  'releaseDate', 'developer', 'publisher',
] as const

export async function applyProviderData(
  gameId: string,
  provider: 'igdb' | 'steam',
  details: ProviderDetails,
  mode: 'import' | 'refresh',
) {
  const origins = await db.query.fieldOrigins.findMany({
    where: eq(fieldOrigins.gameId, gameId),
  })
  const originOf = new Map(origins.map((o) => [o.fieldName, o]))

  const incoming: Record<string, unknown> = {
    title: details.title,
    altTitles: details.altTitles,
    description: details.description ?? null,
    releaseDate: details.releaseDate ?? null,
    developer: details.developer ?? null,
    publisher: details.publisher ?? null,
  }

  const patch: Record<string, unknown> = {}
  const written: string[] = []
  const skipped: string[] = []

  for (const field of PROVIDER_FIELDS) {
    const value = incoming[field]

    // provider has nothing for this field — leave what we have
    if (value === undefined || value === null || value === '') continue

    const origin = originOf.get(field)

    // THE RULE
    if (mode === 'refresh' && origin?.source === 'custom') {
      skipped.push(field)
      continue
    }

    patch[field] = value
    written.push(field)
  }

  if (written.length === 0) return { written: [], skipped }

  await db.transaction(async (tx) => {
    await tx.update(games)
      .set({ ...patch, updatedAt: new Date() })
      .where(eq(games.id, gameId))

    for (const fieldName of written) {
      await tx.insert(fieldOrigins)
        .values({ gameId, fieldName, source: 'provider', provider })
        .onConflictDoUpdate({
          target: [fieldOrigins.gameId, fieldOrigins.fieldName],
          set: { source: 'provider', provider, updatedAt: new Date() },
        })
    }
  })

  return { written, skipped }
}
```

Read the two guard clauses carefully — they're the whole feature:

**`if (value === undefined || null || '') continue`** — a provider that has nothing for a
field must not blank yours. Missing data is not an instruction to delete.

**`if (mode === 'refresh' && origin?.source === 'custom') continue`** — on refresh, a field
you edited is skipped entirely. On import, mode is `'import'` and everything writes, because
there's nothing to protect yet.

The function returns `written` and `skipped` so the UI can tell the truth:
*"Updated cover and release date. Kept your description and title."*

## 11.4 Reverting

The override has to work in both directions, or "custom" becomes a trap.

```ts
export async function revertField(gameId: string, fieldName: string) {
  if (!PROVIDER_FIELDS.includes(fieldName as any)) {
    throw new ApiError('not_revertible', 'That field has no provider value', 400)
  }

  await db.delete(fieldOrigins).where(and(
    eq(fieldOrigins.gameId, gameId),
    eq(fieldOrigins.fieldName, fieldName),
  ))

  // with no origin row, refresh treats it as provider-owned again
  const ids = await db.query.externalIds.findMany({
    where: eq(externalIds.gameId, gameId),
  })
  const igdbId = ids.find((i) => i.provider === 'igdb')
  if (!igdbId) throw new ApiError('no_provider', 'No linked provider', 400)

  const details = await igdb.getDetails(igdbId.externalId)
  return applyProviderData(gameId, 'igdb', details, 'refresh')
}
```

## 11.5 Test this before you trust it

Seriously. Write this test the same day you write the merge.

```ts
// tests/integration/merge.test.ts
test('refresh preserves edits and updates everything else', async () => {
  const game = await importFromProvider(igdbFixture)   // description: "Provider text"

  await updateGame(game.id, { description: 'My own words' })

  const result = await applyProviderData(game.id, 'igdb', {
    ...igdbFixture,
    title: 'Elden Ring: Updated Title',
    description: 'Provider rewrote this',
  }, 'refresh')

  const after = await getGame(game.id)

  expect(after.description).toBe('My own words')            // preserved
  expect(after.title).toBe('Elden Ring: Updated Title')     // updated
  expect(result.skipped).toContain('description')
  expect(result.written).toContain('title')
})

test('a provider with no description does not blank yours', async () => {
  const game = await importFromProvider(igdbFixture)
  await applyProviderData(game.id, 'igdb',
    { ...igdbFixture, description: undefined }, 'refresh')

  const after = await getGame(game.id)
  expect(after.description).toBeTruthy()
})

test('personal fields are never touched', async () => {
  const game = await importFromProvider(igdbFixture)
  await updateRating(game.id, { gameplay: 9.5 })
  await updateGame(game.id, { notes: 'my notes', status: 'playing' })

  await applyProviderData(game.id, 'igdb', igdbFixture, 'refresh')

  const after = await getGame(game.id)
  expect(Number(after.ratingGameplay)).toBe(9.5)
  expect(after.notes).toBe('my notes')
  expect(after.status).toBe('playing')
})
```

If these three pass, the archive keeps its promise. If you refactor the merge later and they
still pass, you didn't break it.

**Checkpoint for Part 2:** you can log in, create a game manually, list and filter games
through the API, import a game from IGDB, edit its description, refresh it, and watch your
edit survive. Part 3 covers files.
