// Epic Games has no sign-in this app can host: you sign in on epicgames.com,
// which then shows a one-time code, and that code is pasted here. The server
// trades it for a sign-in it keeps (encrypted) to read your library.

export interface EpicConnectResult {
  status: "connected";
  display_name: string | null;
}

async function failure(response: Response, action: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = (body as { detail?: unknown } | null)?.detail;
  return new Error(
    typeof detail === "string" && detail
      ? detail
      : `${action}: ${response.status} ${response.statusText}`,
  );
}

export async function fetchEpicLoginUrl(): Promise<string> {
  const response = await fetch("/api/library-sync/epic/login-url", {
    credentials: "include",
  });
  if (!response.ok)
    throw await failure(response, "Could not load the Epic sign-in link");
  return ((await response.json()) as { url: string }).url;
}

export async function connectEpic(code: string): Promise<EpicConnectResult> {
  const response = await fetch("/api/library-sync/epic/connect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ code }),
  });
  if (!response.ok)
    throw await failure(response, "Could not connect Epic Games");
  return (await response.json()) as EpicConnectResult;
}

export async function disconnectEpic(): Promise<void> {
  const response = await fetch("/api/library-sync/epic/connect", {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok)
    throw await failure(response, "Could not disconnect Epic Games");
}
