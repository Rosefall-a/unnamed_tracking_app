export interface AchievementFeedEntry {
  id: string;
  gameId: string;
  gameTitle: string;
  name: string;
  description: string | null;
  iconUrl: string | null;
  unlockedAt: number | null;
  globalPercent: number | null;
}

export interface AchievementsFeed {
  recent: AchievementFeedEntry[];
  rarest: AchievementFeedEntry[];
}

// The latest and the rarest unlocks across every game, for the Home widgets.
export async function fetchAchievementsFeed(
  limit = 12,
): Promise<AchievementsFeed> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true")
    return { recent: [], rarest: [] };
  const response = await fetch(`/api/game/achievements-feed?limit=${limit}`, {
    credentials: "include",
  });
  if (!response.ok)
    throw new Error(`Could not fetch recent achievements: ${response.status}`);
  const raw = (await response.json()) as Record<
    "recent" | "rarest",
    {
      id: string;
      game_id: string;
      game_title: string;
      name: string;
      description: string | null;
      icon_url: string | null;
      unlocked_at: number | null;
      global_percent: number | null;
    }[]
  >;
  const map = (rows: typeof raw.recent): AchievementFeedEntry[] =>
    rows.map((r) => ({
      id: r.id,
      gameId: r.game_id,
      gameTitle: r.game_title,
      name: r.name,
      description: r.description,
      iconUrl: r.icon_url,
      unlockedAt: r.unlocked_at,
      globalPercent: r.global_percent,
    }));
  return { recent: map(raw.recent), rarest: map(raw.rarest) };
}
