import { apiError } from "./apiErrors";

// Library export/import plus admin deployment configuration backup/restore.
export interface ImportResult { created: number; skipped: number; errors: string[] }
export interface BackupStatus { enabled: boolean; interval_hours: number; backups_kept: number; last_backup_at: number | null; backup_count: number }

export async function rotateDeploymentKey(): Promise<{ rotated: boolean; sessions_revoked: boolean; message: string }> {
  const response = await fetch("/api/settings/backup/rotate-key", {
    method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ confirm: true }),
  });
  if (!response.ok) throw await apiError(response, "Failed to rotate encryption key");
  return await response.json();
}


export interface DeploymentBackupOptions {
  password: string;
  include_users?: boolean;
  include_sessions?: boolean;
  full_installation?: boolean;
  save_to_setup_path?: boolean;
}

export async function exportDeploymentBackup(
  options: DeploymentBackupOptions,
): Promise<Blob> {
  const response = await fetch("/api/export/deployment-backup", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options),
  });
  if (!response.ok) {
    const body = await response.text();
    let message = `Deployment backup failed: ${response.status}`;
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      if (parsed.detail) message = parsed.detail;
    } catch {
      if (body) message = `${message} ${body}`;
    }
    throw new Error(message);
  }
  return response.blob();
}
