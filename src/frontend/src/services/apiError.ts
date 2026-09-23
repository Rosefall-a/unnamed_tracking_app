// Turns a failed API response into a sentence a person can act on, instead of
// the raw status line and JSON the server sent.

function serverDetail(body: string): string | null {
  try {
    const detail = (JSON.parse(body) as { detail?: unknown }).detail;
    return typeof detail === "string" ? detail : null;
  } catch {
    return null;
  }
}

export function friendlyError(status: number, body: string): string {
  if (status === 401) return "You are signed out. Sign in again to continue.";
  if (status === 403) return "You do not have permission to do that.";
  if (status === 404)
    return "That could not be found. It may have been deleted.";
  if (status === 422) return "That is not a valid address or value.";
  if (status >= 500) {
    return "The server had a problem. Wait a moment and try again.";
  }
  return serverDetail(body) ?? `The request failed (${status}).`;
}

export async function failedRequest(response: Response): Promise<Error> {
  return new Error(friendlyError(response.status, await response.text()));
}
