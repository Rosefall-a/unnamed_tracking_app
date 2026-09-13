export interface SetupStatus {
  setup_required: boolean;
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
): Promise<void> {
  const response = await fetch("/api/setup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, email, password }),
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Setup failed: ${message}`);
  }
}
