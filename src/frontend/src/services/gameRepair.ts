// Settings > Administration > Repair (see backend api/routes/game_repair.py).
export interface RepairPerson {
  user_id: string;
  username: string;
  games: number;
  problems: Record<string, number>;
  to_fix: number;
  to_fix_forced: number;
  // pictures with no local copy yet, so a page has to fetch them from another site
  offline_missing?: Record<string, number>;
}

export interface RepairGame {
  id: string;
  title: string;
  source: string | null;
  folder: string;
  checked_at: number | null;
}

export interface RepairResult {
  checked: number;
  names: number;
  details: number;
  art: number;
  covers: number;
  dates: number;
  times: number;
  folders: number;
  info_files: number;
  failed: number;
  hltb_error: string | null;
  pictures: number;
}

export interface RepairRun {
  running: boolean;
  who: string;
  done: number;
  total: number;
  result: Partial<RepairResult>;
  error: string | null;
  finished_at: number | null;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/settings/repair${path}`, {
    credentials: "include",
    ...init,
  });
  if (!response.ok) {
    let detail = "";
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // not JSON, the status code will do
    }
    throw new Error(detail || `The repair request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export const scanLibraries = () => request<RepairPerson[]>("/scan");

export const repairStatus = () => request<RepairRun>("/status");

export const gamesWithProblem = (userId: string, problem: string) =>
  request<RepairGame[]>(
    `/games?user_id=${encodeURIComponent(userId)}&problem=${encodeURIComponent(problem)}`,
  );

export const startRepair = (
  userId: string | null,
  force: boolean,
  covers = false,
  pictures = false,
) =>
  request<RepairRun>("/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, force, covers, pictures }),
  });

export const fixOneGame = (gameId: string) =>
  request<RepairResult>(`/games/${encodeURIComponent(gameId)}`, {
    method: "POST",
  });

export interface OldFiles {
  folders: {
    folder: string;
    game_id: string;
    title: string;
    in_trash: boolean;
    files: Record<string, number>;
  }[];
  no_game: string[];
  map_folders: number;
}

export const scanOldFiles = (userId: string) =>
  request<OldFiles>(`/old-files?user_id=${encodeURIComponent(userId)}`);

export const restoreOldFiles = (userId: string) =>
  request<{ copied: number; failed: number }>(
    `/old-files?user_id=${encodeURIComponent(userId)}`,
    { method: "POST" },
  );
