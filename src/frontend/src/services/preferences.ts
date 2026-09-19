// Server-side per-user preferences (calendar options, notification
// toggles). Defaults live on the server; this only carries the shape.

export interface Preferences {
  calendar_game_releases: boolean;
  calendar_game_history: boolean;
  calendar_default_view: "month" | "agenda";
  calendar_week_start: 0 | 1;
  calendar_hide_games: boolean;
  calendar_show_estimated: boolean;
  notify_episode_aired: boolean;
  notify_season_started: boolean;
  notify_sequel_announced: boolean;
  notify_movie_released: boolean;
  notification_retention_days: 0 | 7 | 14 | 30 | 90;
  library_default_layout: "list" | "shelf" | "board";
  lists_default_sort: "name" | "count" | "recent";
  stats_include_plan: boolean;
}

export const DEFAULT_PREFERENCES: Preferences = {
  calendar_game_releases: false,
  calendar_game_history: false,
  calendar_default_view: "month",
  calendar_week_start: 0,
  calendar_hide_games: false,
  calendar_show_estimated: true,
  notify_episode_aired: true,
  notify_season_started: true,
  notify_sequel_announced: true,
  notify_movie_released: true,
  notification_retention_days: 30,
  library_default_layout: "list",
  lists_default_sort: "name",
  stats_include_plan: true,
};

export async function fetchPreferences(): Promise<Preferences> {
  const response = await fetch("/api/preferences", { credentials: "include" });
  if (!response.ok)
    throw new Error(`Failed to load preferences: ${response.status}`);
  return { ...DEFAULT_PREFERENCES, ...(await response.json()) };
}

export async function updatePreferences(
  changes: Partial<Preferences>,
): Promise<Preferences> {
  const response = await fetch("/api/preferences", {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });
  if (!response.ok)
    throw new Error(`Failed to save preferences: ${response.status}`);
  return { ...DEFAULT_PREFERENCES, ...(await response.json()) };
}
