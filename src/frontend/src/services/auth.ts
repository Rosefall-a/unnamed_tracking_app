export interface CurrentUser {
  id: string;
  username: string;
  email: string;
  is_admin: boolean;
  steamgriddb_api_key: string | null;
  // when the profile picture was last saved; null or missing when there is none
  profile_picture_version?: number | null;
}

export interface ApiKeySummary {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  created_at: number;
}

export interface CreatedApiKey {
  api_key: string;
  key_prefix: string;
  name: string;
  scopes: string[];
  warning: string;
}

export async function login(
  usernameOrEmail: string,
  password: string,
): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return;
  }

  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username_or_email: usernameOrEmail, password }),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Invalid username/email or password.");
    }
    const message = await response.text();
    throw new Error(
      `Login failed: ${response.status} ${response.statusText} ${message}`,
    );
  }
}

export async function logout(): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return;
  }
  await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
}

export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return {
      id: "mock",
      username: "MockUser",
      email: "mock@example.com",
      is_admin: true,
      steamgriddb_api_key: null,
    };
  }

  const response = await fetch("/api/auth/me", { credentials: "include" });
  if (response.status === 401) return null;
  if (!response.ok) {
    throw new Error(
      `Failed to fetch current user: ${response.status} ${response.statusText}`,
    );
  }
  return await response.json();
}

export async function updateProfile(
  payload: UpdateProfilePayload,
): Promise<CurrentUser> {
  const response = await fetch("/api/auth/me", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      username: payload.username,
      email: payload.email,
      current_password: payload.currentPassword,
      new_password: payload.newPassword,
      steamgriddb_api_key: payload.steamgriddbApiKey,
    }),
  });

  if (response.status === 401) {
    throw new Error("Current password is incorrect.");
  }
  if (response.status === 409) {
    throw new Error("That username or email is already taken.");
  }
  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Failed to update profile: ${response.status} ${response.statusText} ${message}`,
    );
  }

  return await response.json();
}

export async function fetchApiKeys(): Promise<ApiKeySummary[]> {
  const response = await fetch("/api/auth/api-keys", {
    credentials: "include",
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Failed to load API keys: ${response.status} ${response.statusText} ${message}`,
    );
  }
  return await response.json();
}

export async function createApiKey(name: string): Promise<CreatedApiKey> {
  const response = await fetch("/api/auth/api-keys", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ name, scopes: [] }),
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Failed to create API key: ${response.status} ${response.statusText} ${message}`,
    );
  }
  return await response.json();
}

export async function revokeApiKey(keyId: string): Promise<void> {
  const response = await fetch(`/api/auth/api-keys/${keyId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `Failed to revoke API key: ${response.status} ${response.statusText} ${message}`,
    );
  }
}

export interface UpdateProfilePayload {
  username?: string;
  email?: string;
  currentPassword?: string;
  newPassword?: string;
  steamgriddbApiKey?: string;
}

// resolves to the new picture's version (see CurrentUser.profile_picture_version)
export async function uploadProfilePicture(
  userId: string,
  file: File,
): Promise<number | null> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`/api/user/${userId}/profile-picture`, {
    method: "PUT",
    credentials: "include",
    body: formData,
  });

  if (!response.ok) {
    // the server's own wording ("HEIC pictures are not supported...") is
    // what the user needs, not the status line around it
    const body = await response.json().catch(() => null);
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : `Failed to upload profile picture (${response.status}).`,
    );
  }
  const body = (await response.json().catch(() => null)) as {
    version?: string;
  } | null;
  const version = Number(body?.version);
  return Number.isFinite(version) && version > 0 ? version : Date.now();
}

export function profilePictureUrl(userId: string): string {
  return `/api/user/${userId}/profile-picture`;
}

// The picture's address, or null when the user has none: asking anyway got a
// 404 (and a console error) on every page. The version in the address lets the
// browser keep the picture until a new one is uploaded.
export function profilePictureSrc(user: CurrentUser | null): string | null {
  if (!user?.profile_picture_version) return null;
  return `${profilePictureUrl(user.id)}?v=${user.profile_picture_version}`;
}
