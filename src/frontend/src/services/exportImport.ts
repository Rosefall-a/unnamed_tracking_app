// Library export/import, a portable JSON snapshot of games, for backups
// or moving to a new server. Scoped to game data only, not screenshots/
// saves/bounties, see backend/src/api/routes/export_import.py.

export interface ImportResult {
  created: number;
  skipped: number;
  errors: string[];
}

export async function fetchLibraryExport(): Promise<unknown> {
  const response = await fetch("/api/export/library", {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(
      `Failed to export library: ${response.status} ${response.statusText}`,
    );
  }
  return await response.json();
}

export interface BackupStatus {
  enabled: boolean;
  interval_hours: number;
  backups_kept: number;
  last_backup_at: number | null;
  backup_count: number;
}

export async function fetchBackupStatus(): Promise<BackupStatus> {
  const response = await fetch("/api/export/backup-status", {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(
      `Failed to fetch backup status: ${response.status} ${response.statusText}`,
    );
  }
  return await response.json();
}

export async function importLibrary(games: unknown[]): Promise<ImportResult> {
  const response = await fetch("/api/import/library", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(games),
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Failed to import library: ${response.status} ${response.statusText} ${message}`,
    );
  }
  return await response.json();
}
