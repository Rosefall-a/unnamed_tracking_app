export interface Invitation {
  id: string;
  email: string;
  username: string;
  is_admin: boolean;
  expires_at: number;
  accepted_at?: number | null;
  revoked_at?: number | null;
  created_at?: number;
  status?: "pending" | "accepted" | "revoked" | "expired";
}

export interface CreateInvitationPayload {
  username: string;
  email: string;
  isAdmin: boolean;
}

async function parseError(response: Response, fallback: string): Promise<Error> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return new Error(data.detail);
    if (Array.isArray(data.detail)) {
      const messages = data.detail
        .map((item) => (item && typeof item === "object" && typeof (item as { msg?: unknown }).msg === "string" ? (item as { msg: string }).msg : null))
        .filter((message): message is string => Boolean(message));
      if (messages.length) return new Error(messages.join(" "));
    }
  } catch {
    // Keep the safe fallback below when the server did not return JSON.
  }
  return new Error(`${fallback} (${response.status})`);
}

export async function listInvitations(): Promise<Invitation[]> {
  const response = await fetch("/api/auth/invitations", { credentials: "include" });
  if (!response.ok) throw await parseError(response, "Failed to load invitations");
  return await response.json();
}

export async function createInvitation(payload: CreateInvitationPayload): Promise<Invitation> {
  const response = await fetch("/api/auth/invitations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username: payload.username, email: payload.email, is_admin: payload.isAdmin }),
  });
  if (!response.ok) throw await parseError(response, "Failed to send invitation");
  return await response.json();
}

export async function resendInvitation(id: string): Promise<Invitation> {
  const response = await fetch(`/api/auth/invitations/${id}/resend`, { method: "POST", credentials: "include" });
  if (!response.ok) throw await parseError(response, "Failed to resend invitation");
  return await response.json();
}

export async function revokeInvitation(id: string): Promise<void> {
  const response = await fetch(`/api/auth/invitations/${id}`, { method: "DELETE", credentials: "include" });
  if (!response.ok) throw await parseError(response, "Failed to revoke invitation");
}
