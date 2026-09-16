export async function apiError(
  response: Response,
  fallback: string,
): Promise<Error> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string" && data.detail.trim()) {
      return new Error(data.detail.trim());
    }
    if (Array.isArray(data.detail)) {
      const messages = data.detail
        .map((item) => {
          if (!item || typeof item !== "object") return null;
          const message = (item as { msg?: unknown }).msg;
          return typeof message === "string" && message.trim()
            ? message.trim()
            : null;
        })
        .filter((message): message is string => Boolean(message));
      if (messages.length) return new Error(messages.join(" "));
    }
  } catch {
    // Non-JSON responses use the safe status fallback below.
  }

  const status = response.status ? ` (${response.status})` : "";
  return new Error(`${fallback}${status}`);
}
