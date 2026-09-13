export interface OidcLoginStatus {
  enabled: boolean;
  issuer: string | null;
  default_login_method: "local" | "sso";
  login_button_text: string;
}

export async function oidcLoginStatus(): Promise<OidcLoginStatus> {
  const response = await fetch("/api/auth/oidc/status", { credentials: "include" });
  if (!response.ok) {
    return { enabled: false, issuer: null, default_login_method: "local", login_button_text: "Continue with SSO" };
  }
  const result = await response.json();
  return {
    enabled: result.enabled === true,
    issuer: result.issuer ?? null,
    default_login_method: result.default_login_method === "sso" ? "sso" : "local",
    login_button_text: typeof result.login_button_text === "string" && result.login_button_text.trim()
      ? result.login_button_text.trim()
      : "Continue with SSO",
  };
}

export async function oidcEnabled(): Promise<boolean> {
  return (await oidcLoginStatus()).enabled;
}

export function startOidcLogin(): void {
  window.location.assign("/api/auth/oidc/login");
}
