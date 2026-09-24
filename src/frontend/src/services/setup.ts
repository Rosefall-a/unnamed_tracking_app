export interface SetupStatus {
  setup_required: boolean;
  startup_ui: "auto" | "forced";
  forced: boolean;
}

export interface SetupConfigurationSetting {
  name: string;
  source: "env" | "setup" | "both";
  default: unknown;
  resolved?: unknown;
  required: boolean;
  generated: boolean;
  secret: boolean;
  deprecated?: boolean;
  locked?: boolean;
  description: string;
}

export interface SetupConfiguration {
  settings: SetupConfigurationSetting[];
  startup_mode: string;
  startup_ui: "auto" | "forced";
  forced: boolean;
}

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
}

export async function fetchSetupStatus(): Promise<SetupStatus> {
  const response = await fetch("/api/setup/status", { credentials: "include" });
  if (!response.ok) throw new Error(`Failed to check setup status: ${response.status}`);
  return (await response.json()) as SetupStatus;
}

export async function fetchSetupConfiguration(): Promise<SetupConfiguration> {
  const response = await fetch("/api/setup/configuration", { credentials: "include" });
  if (!response.ok) throw new Error(`Failed to load setup configuration: ${response.status}`);
  return (await response.json()) as SetupConfiguration;
}

export async function createInitialAdmin(
  username: string,
  email: string,
  password: string,
  options: SetupOptions = {},
): Promise<{ status: string; user_id: string; is_admin: boolean }> {
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
      const parsed = JSON.parse(body) as { detail?: string | Array<{ msg?: string }> };
      if (Array.isArray(parsed.detail)) {
        const details = parsed.detail.map((item) => item.msg).filter(Boolean);
        if (details.length) message = details.join(" ");
      } else if (parsed.detail) message = parsed.detail;
    } catch {
      if (body) message = `${message} ${body}`;
    }
    throw new Error(message);
  }
  return (await response.json()) as { status: string; user_id: string; is_admin: boolean };
}
