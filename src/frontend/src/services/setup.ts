export interface SetupStatus { setup_required: boolean; }

export interface SetupOptions {
  oidc_enabled?: boolean;
  oidc_name?: string;
  oidc_issuer_url?: string;
  oidc_client_id?: string;
  oidc_client_secret?: string;
  oidc_scopes?: string;
  oidc_redirect_uri?: string;
  oidc_groups_claim?: string;
  oidc_admin_group?: string;
  oidc_user_match_field?: string;
  oidc_allow_new_users?: boolean;
  oidc_button_text?: string;
  oidc_button_image_url?: string | null;
  oidc_button_color?: string;
  oidc_provider_enabled?: boolean;
  oidc_show_on_login?: boolean;
  oidc_autostart_enabled?: boolean;
  oidc_default_login_method?: string;
  smtp_enabled?: boolean;
  smtp_host?: string;
  smtp_port?: number;
  smtp_username?: string;
  smtp_password?: string;
  smtp_use_tls?: boolean;
  smtp_use_ssl?: boolean;
  smtp_from_email?: string;
  smtp_from_name?: string;
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


export async function importApplicationSettings(
  file: File,
  password: string,
): Promise<void> {
  const form = new FormData();
  form.append("application_file", file);
  form.append("password", password);
  const response = await fetch("/api/setup/import-application", {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!response.ok) {
    const body = await response.text();
    let message = `Application settings import failed: ${response.status}`;
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      if (parsed.detail) message = parsed.detail;
    } catch {
      if (body) message = `${message} ${body}`;
    }
    throw new Error(message);
  }
}
