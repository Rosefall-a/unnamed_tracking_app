// Where you left off in a movie (#191), entered and shown as h:mm.

// Any way people write a time: "72", "1:12", "1h 12m", "1h12", "1h", "45m",
// "1.5h". Blank -> null; anything else -> NaN
export function parseProgressMinutes(value: string): number | null {
  const text = value.trim().toLowerCase();
  if (!text) return null;
  const clock = /^(\d+):([0-5]?\d)$/.exec(text);
  if (clock) return Number(clock[1]) * 60 + Number(clock[2]);
  if (/^\d+$/.test(text)) return Number(text);
  const decimal = /^(\d+(?:\.\d+)?)\s*h(?:ours?|rs?)?$/.exec(text);
  if (decimal) return Math.round(Number(decimal[1]) * 60);
  const words =
    /^(?:(\d+)\s*h(?:ours?|rs?)?)?\s*(?:(\d+)\s*(?:m(?:in(?:ute)?s?)?)?)?$/.exec(
      text,
    );
  if (words && (words[1] || words[2])) {
    const minutes = Number(words[2] ?? 0);
    if (words[1] && minutes > 59) return Number.NaN;
    return Number(words[1] ?? 0) * 60 + minutes;
  }
  return Number.NaN;
}

// 105 -> "1h 45m", 120 -> "2h", 45 -> "45m", 0 -> "0m"
export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (!hours) return `${rest}m`;
  return rest ? `${hours}h ${rest}m` : `${hours}h`;
}

// 72 -> "1:12", 5 -> "0:05"
export function formatProgressMinutes(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return `${hours}:${String(rest).padStart(2, "0")}`;
}

// 0..100, or null when the runtime isn't known
export function progressPercent(
  minutes: number | null,
  runtimeMinutes: number | null,
): number | null {
  if (minutes === null || !runtimeMinutes) return null;
  return Math.min(100, Math.round((minutes / runtimeMinutes) * 100));
}
