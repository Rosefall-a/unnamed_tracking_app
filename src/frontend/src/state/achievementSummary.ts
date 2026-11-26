// Every game's achievement counts and rarest unlock, fetched once for the
// whole library so each cover can mark a 100% game without asking for itself.
import { ref } from "vue";
import {
  fetchAchievementsSummary,
  type AchievementsSummaryEntry,
} from "../services/games";

export const achievementSummary = ref<Record<string, AchievementsSummaryEntry>>(
  {},
);

let loadedAt = 0;
let pending: Promise<void> | null = null;

/** Loads the summary unless it was loaded in the last minute. */
export function ensureAchievementSummary(): Promise<void> {
  if (pending) return pending;
  if (Date.now() - loadedAt < 60_000) return Promise.resolve();
  pending = fetchAchievementsSummary()
    .then((s) => {
      achievementSummary.value = s;
      loadedAt = Date.now();
    })
    .catch(() => {
      // covers just show no counts until the next try
    })
    .finally(() => {
      pending = null;
    });
  return pending;
}
