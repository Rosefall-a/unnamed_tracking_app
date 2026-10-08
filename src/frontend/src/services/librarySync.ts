export interface LibrarySyncResult {
  games_added: number;
  games_updated: number;
  achievements_synced: number;
  // every title the sync touched, in the order it processed them, used to
  // animate a completion feed once the (single, all-at-once) request
  // resolves. Not truly live during the request itself; the backend has no
  // streaming endpoint for this yet.
  games: string[];
  // Steam only: wishlist games added, games whose store details, tags or
  // artwork could not be filled in (they keep what they have), games whose
  // unlocked achievements Steam would not share, and games whose achievements
  // could not be read this time (Steam busy; the next sync tries again)
  wishlist_added?: number;
  enrich_failed?: number;
  achievements_unavailable?: string[];
  achievements_failed?: number;
}

export type LibrarySyncProvider =
  "steam" | "psn" | "retroachievements" | "epic";

// A long import reports each step as it goes ("Reading achievements", 40 of
// 120 games), so the caller can show real progress instead of a spinner.
export type SyncProgress = (step: string, done: number, total: number) => void;

export async function syncLibrary(
  provider: LibrarySyncProvider,
  onProgress?: SyncProgress,
): Promise<LibrarySyncResult> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return {
      games_added: 0,
      games_updated: 0,
      achievements_synced: 0,
      games: [],
    };
  }

  if (provider === "epic") return await syncEpic(onProgress);

  // Steam's achievements are read in batches afterwards (see
  // finishSteamImport): reading them all in this one request ran past the
  // proxy's timeout for any sizable library, and the import then failed
  // before the new games got their artwork.
  const query = provider === "steam" ? "?achievements=later" : "";
  const response = await fetch(`/api/library-sync/${provider}${query}`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Library sync failed: ${await errorDetail(response)}`);
  }
  const result: SteamSyncResponse = await response.json();
  if (provider === "steam") await finishSteamImport(result, onProgress);
  return result;
}

// FastAPI's `{"detail": "..."}` message when there is one (Steam saying the
// profile is private, say), else the status line.
async function errorDetail(response: Response): Promise<string> {
  const text = await response.text();
  try {
    const detail = (JSON.parse(text) as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail) return detail;
  } catch {
    // not JSON: fall through to the status line
  }
  return `${response.status} ${response.statusText}`.trim();
}

type SteamSyncResponse = LibrarySyncResult & {
  enrich_game_ids?: string[];
  achievement_game_ids?: string[];
  status_game_ids?: string[];
};

// Saving the games is quick; reading each game's achievements (two or three
// Steam requests) and each new game's store page, tags and artwork (about a
// second) is not. The server does those a few games at a time, so one request
// never runs long enough to time out.
const ACHIEVEMENT_BATCH = 10;
const ENRICH_BATCH = 5;

async function postSteamStep<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/library-sync/steam/${path}`, {
    method: "POST",
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok)
    throw new Error(`Steam import step failed: ${await errorDetail(response)}`);
  return (await response.json()) as T;
}

async function finishSteamImport(
  result: SteamSyncResponse,
  onProgress?: SyncProgress,
): Promise<void> {
  const achievementIds = result.achievement_game_ids ?? [];
  const settle = new Set(result.status_game_ids ?? []);
  const unavailable = [...(result.achievements_unavailable ?? [])];
  let achievementsFailed = 0;
  for (let i = 0; i < achievementIds.length; i += ACHIEVEMENT_BATCH) {
    onProgress?.("Reading achievements", i, achievementIds.length);
    const gameIds = achievementIds.slice(i, i + ACHIEVEMENT_BATCH);
    try {
      const batch = await postSteamStep<{
        achievements_synced: number;
        achievements_unavailable: string[];
      }>("achievements", {
        game_ids: gameIds,
        status_game_ids: gameIds.filter((id) => settle.has(id)),
      });
      result.achievements_synced += batch.achievements_synced;
      unavailable.push(...batch.achievements_unavailable);
    } catch {
      // the games are saved; their achievements come in on the next sync
      achievementsFailed += gameIds.length;
    }
  }
  result.achievements_unavailable = unavailable;
  result.achievements_failed = achievementsFailed;

  const ids = [...(result.enrich_game_ids ?? [])];
  // the wishlist is an extra: if Steam won't give it, the owned games still
  // need their store details and artwork
  try {
    const wishlist = await postSteamStep<{ added: number; game_ids: string[] }>(
      "wishlist",
    );
    result.wishlist_added = wishlist.added;
    ids.push(...wishlist.game_ids);
  } catch {
    result.wishlist_added = 0;
  }
  let failed = 0;
  for (let i = 0; i < ids.length; i += ENRICH_BATCH) {
    onProgress?.("Adding artwork and details", i, ids.length);
    try {
      const batch = await postSteamStep<{ failed: number }>("enrich", {
        game_ids: ids.slice(i, i + ENRICH_BATCH),
      });
      failed += batch.failed;
    } catch {
      failed += ids.slice(i, i + ENRICH_BATCH).length;
    }
  }
  result.enrich_failed = failed;
}

interface EpicSyncStep extends LibrarySyncResult {
  pending: number;
  remaining: number;
  next: string | null;
}

// Epic's library only lists ids, so each new game needs its own catalog
// lookup and artwork. The server adds a few per request and says where to
// carry on (`next`); the first request's update count is the real one, later
// ones also count the games the earlier requests just added.
async function syncEpic(onProgress?: SyncProgress): Promise<LibrarySyncResult> {
  const result: LibrarySyncResult = {
    games_added: 0,
    games_updated: 0,
    achievements_synced: 0,
    games: [],
  };
  let after: string | null = null;
  let total: number | null = null;
  for (let step = 0; ; step++) {
    const query: string = after ? `?after=${encodeURIComponent(after)}` : "";
    const response = await fetch(`/api/library-sync/epic${query}`, {
      method: "POST",
      credentials: "include",
    });
    if (!response.ok)
      throw new Error(`Library sync failed: ${await errorDetail(response)}`);
    const batch = (await response.json()) as EpicSyncStep;
    if (step === 0) result.games_updated = batch.games_updated;
    result.games_added += batch.games_added;
    result.games.push(...batch.games);
    if (!batch.next) return result;
    total ??= batch.pending;
    onProgress?.("Adding games", total - batch.remaining, total);
    after = batch.next;
  }
}

export interface SteamTagsBatch {
  total: number;
  offset: number;
  processed: number;
  updated: number;
  done: boolean;
}

// Re-reads the genres of the Steam games from the tags players vote on. The
// server does a few at a time, so ask again with the next offset until `done`.
export async function refreshSteamTags(
  offset: number,
  limit = 10,
): Promise<SteamTagsBatch> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return { total: 0, offset, processed: 0, updated: 0, done: true };
  }
  const response = await fetch(
    `/api/library-sync/steam-tags/refresh?offset=${offset}&limit=${limit}`,
    { method: "POST", credentials: "include" },
  );
  if (!response.ok) {
    throw new Error(
      `Could not update the tags: ${response.status} ${response.statusText}`,
    );
  }
  return await response.json();
}
