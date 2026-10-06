// What you add on top of a game's achievements: which ones you've pinned, a
// note on each, and one overall note for hunting the game. The backend has no
// place for these yet, so they live in localStorage per game, the same tier as
// collection details and cover picks, and move to the backend when it can
// hold them.
export interface AchievementLocal {
  pins: string[];
  notes: Record<string, string>;
  overall: string;
}

const key = (gameId: string) => `achievementLocal:${gameId}`;

export function loadAchievementLocal(gameId: string): AchievementLocal {
  try {
    const raw = localStorage.getItem(key(gameId));
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<AchievementLocal>;
      return {
        pins: Array.isArray(parsed.pins) ? parsed.pins : [],
        notes: parsed.notes ?? {},
        overall: parsed.overall ?? "",
      };
    }
  } catch {
    // unreadable storage just means starting empty
  }
  return { pins: [], notes: {}, overall: "" };
}

export function saveAchievementLocal(gameId: string, data: AchievementLocal) {
  try {
    localStorage.setItem(key(gameId), JSON.stringify(data));
  } catch {
    // best-effort, the change just won't survive a reload
  }
}
