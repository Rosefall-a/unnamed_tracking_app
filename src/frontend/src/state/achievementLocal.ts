// What you add on top of a game's achievements: which ones you've pinned, a
// note on each, and one overall note for hunting the game. Saved on the server
// per game with the person's other page choices (state/uiState.ts).
import { getUi, setUi } from "./uiState";

export interface AchievementLocal {
  pins: string[];
  notes: Record<string, string>;
  overall: string;
}

const key = (gameId: string) => `achievementLocal:${gameId}`;

export function loadAchievementLocal(gameId: string): AchievementLocal {
  const parsed = getUi<Partial<AchievementLocal> | null>(key(gameId), null);
  return {
    pins: Array.isArray(parsed?.pins) ? [...parsed.pins] : [],
    notes: { ...(parsed?.notes ?? {}) },
    overall: parsed?.overall ?? "",
  };
}

export function saveAchievementLocal(gameId: string, data: AchievementLocal) {
  setUi(key(gameId), data);
}
