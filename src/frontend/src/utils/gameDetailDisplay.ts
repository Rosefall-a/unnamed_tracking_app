import type { Achievement, AchievementTier } from "../types/game";

export function displayFileName(filename: string): string {
  // strip the random 8-char dedupe prefix save_media_bytes adds
  const parts = filename.split("_");
  return parts.length > 1 ? parts.slice(1).join("_") : filename;
}

export function sortedAchievements(achievements: Achievement[]) {
  return [...achievements].sort((a, b) => {
    if (a.unlockedAt === null && b.unlockedAt === null) return 0;
    if (a.unlockedAt === null) return 1;
    if (b.unlockedAt === null) return -1;
    return b.unlockedAt.localeCompare(a.unlockedAt);
  });
}

export function deriveTier(achievement: Achievement): AchievementTier {
  if (achievement.tierOverride) return achievement.tierOverride;
  const rarity = achievement.rarityPercent;
  if (rarity === null || rarity === undefined) return "bronze";
  if (rarity <= 20) return "gold";
  if (rarity <= 50) return "silver";
  return "bronze";
}

export function formatUnlockedAt(dateStr: string) {
  const d = new Date(dateStr);
  return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
}

export function formatPlaytime(minutes: number) {
  if (minutes === 0) return "Not played yet";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}
