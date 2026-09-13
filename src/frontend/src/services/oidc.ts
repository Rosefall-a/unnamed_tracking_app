export async function oidcEnabled(): Promise<boolean> {
  const response = await fetch("/api/auth/oidc/status", { credentials: "include" });
  if (!response.ok) return false;
  return (await response.json()).enabled === true;
}

export function startOidcLogin(): void {
  window.location.assign("/api/auth/oidc/login");
}
