import { apiError } from "./apiErrors";

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

export interface CreateInvitationPayload { username: string; email: string; isAdmin: boolean; }

export async function listInvitations(): Promise<Invitation[]> {
  const response = await fetch("/api/auth/invitations", { credentials: "include" });
  if (!response.ok) throw await apiError(response, "Failed to load invitations");
  return await response.json();
}

export async function createInvitation(payload: CreateInvitationPayload): Promise<Invitation> {
  const response = await fetch("/api/auth/invitations", {
    method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
    body: JSON.stringify({ username: payload.username, email: payload.email, is_admin: payload.isAdmin }),
  });
  if (!response.ok) throw await apiError(response, "Failed to send invitation");
  return await response.json();
}

export async function resendInvitation(id: string): Promise<Invitation> {
  const response = await fetch(`/api/auth/invitations/${id}/resend`, { method: "POST", credentials: "include" });
  if (!response.ok) throw await apiError(response, "Failed to resend invitation");
  return await response.json();
}

export async function revokeInvitation(id: string): Promise<void> {
  if (!window.confirm("Revoke this invitation? The invitation link will no longer work.")) return;
  const response = await fetch(`/api/auth/invitations/${id}`, { method: "DELETE", credentials: "include" });
  if (!response.ok) throw await apiError(response, "Failed to revoke invitation");
}
