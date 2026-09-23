// Formats a unix-seconds "next episode airs at" timestamp into a short
// countdown string, shared by the Episodes tab header and per-episode
// badge on both AnimeDetail.vue and TVShowDetail.vue.
export function formatAiringCountdown(airAtSeconds: number): string {
  const diffMs = airAtSeconds * 1000 - Date.now();
  if (diffMs <= 0) return "Aired";
  const days = Math.floor(diffMs / 86_400_000);
  const hours = Math.floor((diffMs % 86_400_000) / 3_600_000);
  if (days > 0) return `${days}d ${hours}h`;
  const minutes = Math.floor((diffMs % 3_600_000) / 60_000);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}
