export interface LibrarySyncResult {
  games_added: number;
  games_updated: number;
  achievements_synced: number;
  // every title the sync touched, in the order it processed them, used to
  // animate a completion feed once the (single, all-at-once) request
  // resolves. Not truly live during the request itself; the backend has no
  // streaming endpoint for this yet.
  games: string[];
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
  return await response.json();
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
