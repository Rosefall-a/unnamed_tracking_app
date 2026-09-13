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
  if (!response.ok) throw new Error(`Failed to check setup status: ${response.status}`);
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
