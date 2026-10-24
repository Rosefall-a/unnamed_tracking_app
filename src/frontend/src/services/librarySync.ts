import { invalidateGameList } from "./games";

export interface LibrarySyncResult {
  games_added: number;
  games_updated: number;
  achievements_synced: number;
  // every title the import touched, in the order it processed them, used to
  // animate a completion feed once the import has finished
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

// An import runs on the server from start to finish (store details, artwork,
// achievements, the wishlist), so closing or reloading the page no longer stops
// it. The app starts it and then only reads its progress.
export interface LibraryImportJob {
  provider: LibrarySyncProvider;
  running: boolean;
  step: string;
  done: number;
  total: number;
  result: LibrarySyncResult;
  error: string | null;
}

const POLL_MS = 1500;
// a few missed progress checks (a network blip) are not a failed import:
// the import keeps running on the server either way
const MISSED_POLLS_ALLOWED = 5;

export const LIBRARY_SYNC_PROVIDER_LABELS: Record<LibrarySyncProvider, string> =
  {
    steam: "Steam",
    psn: "PlayStation",
    retroachievements: "RetroAchievements",
    epic: "Epic Games",
  };

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
  const response = await fetch(`/api/library-sync/import/${provider}`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Library sync failed: ${await errorDetail(response)}`);
  }
  const job = (await response.json()) as LibraryImportJob;
  if (job.provider !== provider) {
    const running = LIBRARY_SYNC_PROVIDER_LABELS[job.provider];
    throw new Error(
      `A ${running} import is still running. Try again when it has finished.`,
    );
  }
  return await waitForLibraryImport(onProgress);
}

/** The running or most recent import, or null if there has been none since
 * the server started. */
export async function fetchLibraryImport(): Promise<LibraryImportJob | null> {
  const response = await fetch("/api/library-sync/import/status", {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(
      `Could not read the import: ${await errorDetail(response)}`,
    );
  }
  return (await response.json()) as LibraryImportJob | null;
}

/** Follows the server's import until it ends, reporting each step. */
export async function waitForLibraryImport(
  onProgress?: SyncProgress,
): Promise<LibrarySyncResult> {
  let missed = 0;
  try {
    while (true) {
      let job: LibraryImportJob | null;
      try {
        job = await fetchLibraryImport();
        missed = 0;
      } catch (e) {
        if (++missed > MISSED_POLLS_ALLOWED)
          throw new Error(
            "Lost contact with the server. The import keeps running there; check back in a moment.",
            { cause: e },
          );
        await new Promise((r) => setTimeout(r, POLL_MS));
        continue;
      }
      if (!job) throw new Error("The server has no import running.");
      if (!job.running) {
        if (job.error) throw new Error(`Library sync failed: ${job.error}`);
        return job.result;
      }
      onProgress?.(job.step, job.done, job.total);
      await new Promise((r) => setTimeout(r, POLL_MS));
    }
  } finally {
    // the import added and changed games on the server, even if it failed
    invalidateGameList();
  }
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
  invalidateGameList();
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
