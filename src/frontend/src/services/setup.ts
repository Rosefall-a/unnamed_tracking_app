export interface SetupStatus {
  setup_required: boolean;
}

export interface SetupOptions {
  oidc_enabled?: boolean;
  oidc_issuer_url?: string;
  oidc_client_id?: string;
  oidc_client_secret?: string;
  oidc_scopes?: string;
  oidc_redirect_uri?: string;
  oidc_groups_claim?: string;
  oidc_admin_group?: string;
  oidc_user_match_field?: string;
}

export async function fetchSetupStatus(): Promise<SetupStatus> {
  const response = await fetch("/api/setup/status", { credentials: "include" });
  if (!response.ok)
    throw new Error(`Failed to check setup status: ${response.status}`);
  return await response.json();
}

export async function createInitialAdmin(
  username: string,
  email: string,
  password: string,
  options: SetupOptions = {},
): Promise<void> {
  const response = await fetch("/api/setup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, email, password, ...options }),
  });
  if (!response.ok) {
    const body = await response.text();
    let message = `Setup failed: ${response.status}`;
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      if (parsed.detail) message = parsed.detail;
    } catch {
      if (body) message = `${message} ${body}`;
    }
    throw new Error(message);
  }
}

export interface ApplicationBackupPreview {
  options: Record<string, boolean>;
  has_users: boolean;
  has_sessions: boolean;
  oidc: Record<string, unknown>;
}

export async function fetchApplicationBackupStatus(): Promise<{available: boolean}> {
  const response = await fetch("/api/setup/application-backup", {credentials: "include"});
  if (!response.ok) throw new Error("Unable to check for a preconfigured application backup.");
  return await response.json();
}

export async function previewApplicationBackup(password: string, file?: File): Promise<ApplicationBackupPreview> {
  const form = new FormData();
  form.append("password", password);
  if (file) form.append("application_file", file);
  const response = await fetch("/api/setup/application-backup/preview", {method: "POST", credentials: "include", body: form});
  if (!response.ok) throw new Error(await response.text());
  return await response.json();
}

export async function importApplicationBackup(password: string, file?: File): Promise<Record<string, boolean>> {
  const form = new FormData();
  form.append("password", password);
  if (file) form.append("application_file", file);
  const response = await fetch("/api/setup/import-application", {method: "POST", credentials: "include", body: form});
  if (!response.ok) throw new Error(await response.text());
  return await response.json();
}
