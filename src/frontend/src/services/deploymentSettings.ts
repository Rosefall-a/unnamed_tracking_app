export interface DeploymentSettings {
  providers: Record<string, string | boolean | null>;
  oidc: {
    issuer_url: string | null;
    client_id: string | null;
    scopes: string | null;
    redirect_uri: string | null;
    groups_claim: string | null;
    admin_group: string | null;
    client_secret_configured: boolean;
  };
}

export async function fetchDeploymentSettings(): Promise<DeploymentSettings> {
  const response = await fetch("/api/settings/deployment", { credentials: "include" });
  if (!response.ok) throw new Error(`Failed to load server integrations: ${response.status}`);
  return await response.json();
}

export async function updateDeploymentSettings(payload: Record<string, string>): Promise<DeploymentSettings> {
  const response = await fetch("/api/settings/deployment", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Failed to save server integrations: ${response.status} ${message}`);
  }
  return await response.json();
}
