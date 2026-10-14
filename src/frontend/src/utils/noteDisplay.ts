// How a note is shown on a card: its dates, its word count and the start of
// its text. Shared by the Notes tab and an achievement's own page.
import type { GameNoteSummary } from "../services/games";

export const dateFormat = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric",
});

export function when(seconds: number): string {
  return seconds ? dateFormat.format(new Date(seconds * 1000)) : "";
}

export function excerpt(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/^\s{0,3}#{1,6}\s*/gm, "")
    .replace(/^\s*[-*+]\s+\[[ xX]\]\s*/gm, "☐ ")
    .replace(/^\s*[-*+]\s+/gm, "• ")
    .replace(/[*_`>~]/g, "")
    .replace(/\n{2,}/g, "\n")
    .trim()
    .slice(0, 280);
}

export function dates(n: GameNoteSummary): string {
  const created = when(n.created_at);
  const edited = when(n.updated_at);
  if (!created) return edited ? `Edited ${edited}` : "";
  return created === edited || !edited
    ? `Created ${created}`
    : `Created ${created} · edited ${edited}`;
}

export function wordLabel(n: number): string {
  return `${n.toLocaleString()} word${n === 1 ? "" : "s"}`;
}
