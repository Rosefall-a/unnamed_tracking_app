// Pairs of library entries that may be the same game: one the person made and one a
// Steam sync created. The server never merges them on its own.

export type MatchStatus = "pending" | "kept_both" | "merged";
export type Prefer = "mine" | "steam";

export interface MatchGame {
  id: string;
  title: string;
  coverUrl: string;
  source: string | null;
  status: string;
  rating: number | null;
  platform: string | null;
  playtimeSeconds: number;
  releaseDate: string | null;
  achievements: number;
  notes: number;
  screenshots: number;
  deleted: boolean;
}

export interface GameMatch {
  id: string;
  status: MatchStatus;
  prefer: Prefer | null;
  createdAt: number;
  resolvedAt: number | null;
  original: MatchGame;
  steam: MatchGame;
}

interface BackendGame {
  id: string;
  title: string;
  cover_url: string;
  source: string | null;
  status: string;
  rating: number | null;
  platform: string | null;
  playtime_seconds: number;
  release_date: string | null;
  achievements: number;
  notes: number;
  screenshots: number;
  deleted: boolean;
}

interface BackendMatch {
  id: string;
  status: MatchStatus;
  prefer: Prefer | null;
  created_at: number;
  resolved_at: number | null;
  original: BackendGame;
  steam: BackendGame;
}

function mapGame(g: BackendGame): MatchGame {
  return {
    id: g.id,
    title: g.title,
    coverUrl: g.cover_url,
    source: g.source,
    status: g.status,
    rating: g.rating,
    platform: g.platform,
    playtimeSeconds: g.playtime_seconds,
    releaseDate: g.release_date,
    achievements: g.achievements,
    notes: g.notes,
    screenshots: g.screenshots,
    deleted: g.deleted,
  };
}

function mapMatch(m: BackendMatch): GameMatch {
  return {
    id: m.id,
    status: m.status,
    prefer: m.prefer,
    createdAt: m.created_at,
    resolvedAt: m.resolved_at,
    original: mapGame(m.original),
    steam: mapGame(m.steam),
  };
}

async function request<T>(
  path: string,
  action: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(`/api/game-matches${path}`, {
    method: body === undefined && path === "" ? "GET" : "POST",
    credentials: "include",
    headers:
      body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = "";
    try {
      detail = (await response.json()).detail ?? "";
    } catch {
      // no body
    }
    throw new Error(detail || `Could not ${action}.`);
  }
  return (await response.json()) as T;
}

export async function fetchMatches(): Promise<{
  items: GameMatch[];
  pending: number;
}> {
  const raw = await request<{ items: BackendMatch[]; pending: number }>(
    "",
    "load the possible duplicates",
  );
  return { items: raw.items.map(mapMatch), pending: raw.pending };
}

export async function fetchMatchesForGame(
  gameId: string,
): Promise<GameMatch[]> {
  const response = await fetch(`/api/game-matches/for/${gameId}`, {
    credentials: "include",
  });
  if (!response.ok) return [];
  return ((await response.json()) as BackendMatch[]).map(mapMatch);
}

export async function scanForMatches(): Promise<number> {
  return (await request<{ found: number }>("/scan", "look for duplicates", {}))
    .found;
}

export async function mergeMatch(
  id: string,
  prefer: Prefer,
): Promise<GameMatch> {
  return mapMatch(
    await request<BackendMatch>(`/${id}/merge`, "merge these games", {
      prefer,
    }),
  );
}

export async function keepBoth(id: string): Promise<GameMatch> {
  return mapMatch(
    await request<BackendMatch>(`/${id}/keep-both`, "keep both", {}),
  );
}

// undo a merge, or ask again about a pair that was kept apart
export async function reopenMatch(id: string): Promise<GameMatch> {
  return mapMatch(
    await request<BackendMatch>(`/${id}/reopen`, "reopen this", {}),
  );
}
