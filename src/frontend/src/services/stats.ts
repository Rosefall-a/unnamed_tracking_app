export interface StatsBreakdownEntry {
  label: string;
  count: number;
}

export interface MostPlayedEntry {
  id: string;
  title: string;
  playtime_seconds: number;
}

export interface RecentlyAddedEntry {
  month: string;
  count: number;
}

export interface StatsOverview {
  total_games: number;
  favorite_count: number;
  total_playtime_seconds: number;
  storage_used_bytes: number;
  total_spent: number;
  average_rating: number | null;
  status_breakdown: StatsBreakdownEntry[];
  source_breakdown: StatsBreakdownEntry[];
  most_played: MostPlayedEntry[];
  recently_added: RecentlyAddedEntry[];
  rating_histogram: StatsBreakdownEntry[];
  top_tags: StatsBreakdownEntry[];
  release_year_breakdown: StatsBreakdownEntry[];
  format_breakdown: StatsBreakdownEntry[];
}

const MOCK_STATS: StatsOverview = {
  total_games: 0,
  favorite_count: 0,
  total_playtime_seconds: 0,
  storage_used_bytes: 0,
  total_spent: 0,
  average_rating: null,
  status_breakdown: [],
  source_breakdown: [],
  most_played: [],
  recently_added: [],
  rating_histogram: [],
  top_tags: [],
  release_year_breakdown: [],
  format_breakdown: [],
};

export async function fetchStatsOverview(): Promise<StatsOverview> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return { ...MOCK_STATS };
  }

  const response = await fetch("/api/stats/overview", {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(
      `Could not fetch stats: ${response.status} ${response.statusText}`,
    );
  }
  return await response.json();
}

export interface WeeklyDigest {
  period_start: number;
  games_played: number;
  games_added: number;
  achievements_unlocked: number;
  metadata_changes: number;
}

const MOCK_WEEKLY_DIGEST: WeeklyDigest = {
  period_start: 0,
  games_played: 0,
  games_added: 0,
  achievements_unlocked: 0,
  metadata_changes: 0,
};

export async function fetchWeeklyDigest(): Promise<WeeklyDigest> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    return { ...MOCK_WEEKLY_DIGEST };
  }

  const response = await fetch("/api/stats/weekly-digest", {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(
      `Could not fetch weekly digest: ${response.status} ${response.statusText}`,
    );
  }
  return await response.json();
}

// Achievement milestones (backend features/achievement_milestones.py), worked
// out from the unlock times: newest first, plus the next one of each kind.
export interface AchievementMilestone {
  id: string;
  kind: "unlocks" | "perfect" | "rarity";
  label: string;
  // null when an unlock had no time, so the moment cannot be known
  at: number | null;
  game_id: string | null;
  game_title: string | null;
  achievement: string | null;
}

export interface NextMilestone {
  kind: "unlocks" | "perfect";
  label: string;
  current: number;
  target: number;
}

export interface AchievementMilestones {
  reached: AchievementMilestone[];
  next: NextMilestone[];
  totals: { unlocked: number; perfect: number };
}

export async function fetchAchievementMilestones(): Promise<AchievementMilestones> {
  const response = await fetch("/api/stats/achievement-milestones", {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Could not load milestones: ${response.status}`);
  }
  return await response.json();
}

// every unlock time and every time a game became perfect (seconds), for goals
// counted over a year or month; totals also count unlocks with no time
export interface AchievementTimes {
  unlocks: number[];
  perfect: number[];
  totals: { unlocked: number; perfect: number };
}

export async function fetchAchievementTimes(): Promise<AchievementTimes> {
  const response = await fetch("/api/stats/achievement-times", {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Could not load achievement times: ${response.status}`);
  }
  return await response.json();
}
