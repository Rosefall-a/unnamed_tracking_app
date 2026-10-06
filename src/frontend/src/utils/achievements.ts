// Small helpers shared by the Achievements tab and an achievement's own page.
import type { Achievement, AchievementKind } from "../types/game";

// PlayStation and RetroAchievements unlocks have no stored time, so "unlocked"
// can't be read from the time alone: use the flag the API sends when there is
// one, and fall back to the time only for data that predates it.
export function isUnlocked(a: Achievement): boolean {
  return a.unlocked ?? a.unlockedAt !== null;
}

export const KIND_LABEL: Record<AchievementKind, string> = {
  progression: "Progression",
  missable: "Missable",
  win_condition: "Win condition",
};

// providers spell the type differently ("win_condition", "Win Condition")
export function normalizeKind(
  raw: string | null | undefined,
): AchievementKind | null {
  const key = (raw ?? "")
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
  return key in KIND_LABEL ? (key as AchievementKind) : null;
}

// the share of all players who have it, one decimal like Steam shows it
export function formatPercent(percent: number): string {
  if (percent > 0 && percent < 0.1) return "<0.1%";
  return `${percent.toFixed(1)}%`;
}

export function unlockedOn(iso: string): { date: string; time: string } {
  const d = new Date(iso);
  return {
    date: d.toLocaleDateString(),
    time: d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
  };
}
