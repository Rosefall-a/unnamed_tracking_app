// The date shown for an uploaded file. The server works out when it was really
// taken (photo data, then the file name, then the file's modified date, then
// the upload) and says which of those it used. Dates read from photo data, a
// file name or typed by hand have no time zone, so they are shown as written;
// the other two are real moments and show in the viewer's own zone.

export type DateSource =
  | "photo"
  | "video"
  | "filename"
  | "file"
  | "uploaded"
  | "manual"
  | "achievement";

interface Dated {
  created_at: number;
  taken_at?: number | null;
  taken_source?: DateSource | null;
}

export const SOURCE_LABEL: Record<DateSource, string> = {
  photo: "Read from the photo data",
  video: "Read from the video data",
  achievement: "Taken from the achievement's unlock time",
  filename: "Read from the file name",
  file: "From the file's modified date",
  uploaded: "The day it was uploaded",
  manual: "Set by you",
};

export function mediaSeconds(item: Dated): number {
  return item.taken_at ?? item.created_at;
}

export function mediaSource(item: Dated): DateSource {
  return item.taken_at == null ? "uploaded" : (item.taken_source ?? "file");
}

function zoneFor(source: DateSource): string | undefined {
  return source === "photo" || source === "filename" || source === "manual"
    ? "UTC"
    : undefined;
}

export function formatMediaDate(item: Dated): string {
  if (!mediaSeconds(item)) return "";
  return new Date(mediaSeconds(item) * 1000).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: zoneFor(mediaSource(item)),
  });
}

// Dates the file gave us or the user chose are trustworthy; "uploaded" and
// "file" are guesses that a better source may replace.
export function isGuess(item: Dated): boolean {
  const s = mediaSource(item);
  return s === "uploaded" || s === "file";
}

// An achievement's unlock time in seconds, or null when it has none.
export function unlockSeconds(
  achievement: { unlockedAt: string | null } | undefined | null,
): number | null {
  if (!achievement?.unlockedAt) return null;
  const ms = Date.parse(achievement.unlockedAt);
  return Number.isNaN(ms) ? null : Math.floor(ms / 1000);
}

const PREF_KEY = "mediaDateFromAchievement";
// Whether tying a file to an achievement also takes the achievement's unlock
// time as its date. On by default, and only ever replaces a guessed date.
export function dateFromAchievementPref(): boolean {
  try {
    return localStorage.getItem(PREF_KEY) !== "off";
  } catch {
    return true;
  }
}
export function setDateFromAchievementPref(on: boolean): void {
  try {
    localStorage.setItem(PREF_KEY, on ? "on" : "off");
  } catch {
    // the choice just will not be remembered
  }
}

// "2026-05-15", what a date input shows, in the same zone as the label
export function dateInputValue(item: Dated): string {
  return new Date(mediaSeconds(item) * 1000).toLocaleDateString("en-CA", {
    timeZone: zoneFor(mediaSource(item)),
  });
}

// a typed date is stored as midnight UTC and shown back as the same day
export function secondsFromDateInput(value: string): number | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!m) return null;
  return Math.floor(Date.UTC(+m[1], +m[2] - 1, +m[3]) / 1000);
}
