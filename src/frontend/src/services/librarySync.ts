export interface LibrarySyncResult {
  games_added: number;
  games_updated: number;
  achievements_synced: number;
  // every title the sync touched, in the order it processed them, used to
  // animate a completion feed once the (single, all-at-once) request
  // resolves. Not truly live during the request itself; the backend has no
  // streaming endpoint for this yet.
  games: string[];
  // Steam only: wishlist games added, and games whose store details, tags or
  // artwork could not be filled in (they keep what they have)
  wishlist_added?: number;
  enrich_failed?: number;
}

export type LibrarySyncProvider = "steam" | "psn" | "retroachievements";

export async function syncLibrary(
  provider: LibrarySyncProvider,
): Promise<LibrarySyncResult> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return {
      games_added: 0,
      games_updated: 0,
      achievements_synced: 0,
      games: [],
    };
  }

  const response = await fetch(`/api/library-sync/${provider}`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Library sync failed: ${response.status} ${response.statusText} ${message}`,
    );
  }
  const result: LibrarySyncResult & { enrich_game_ids?: string[] } =
    await response.json();
  if (provider === "steam") await finishSteamImport(result);
  return result;
}

// Saving the games is quick; reading each new game's store page, tags and
// artwork is not (about a second each). The server does that a few games at a
// time, so one request never runs long enough to time out.
const ENRICH_BATCH = 5;

async function postSteamStep<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/library-sync/steam/${path}`, {
    method: "POST",
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok)
    throw new Error(`Steam import step failed: ${response.status}`);
  return (await response.json()) as T;
}

async function finishSteamImport(
  result: LibrarySyncResult & { enrich_game_ids?: string[] },
): Promise<void> {
  const ids = [...(result.enrich_game_ids ?? [])];
  const wishlist = await postSteamStep<{ added: number; game_ids: string[] }>(
    "wishlist",
  );
  result.wishlist_added = wishlist.added;
  ids.push(...wishlist.game_ids);
  let failed = 0;
  for (let i = 0; i < ids.length; i += ENRICH_BATCH) {
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
