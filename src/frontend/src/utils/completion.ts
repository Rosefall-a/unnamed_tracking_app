// Knowing when a show is finished, and asking about it. A show whose last episode
// has been watched should be marked Completed: the Library's "+" button and quick
// edit, and the Episodes tab, all ask the same question the same way.
import { useConfirm } from "../state/dialog";
import { statusBucket } from "./mediaStatus";

interface SeasonLike {
  episodeCount: number | null;
  episodesWatched: number;
  episodes?: { watched: boolean }[];
}
export interface ShowLike {
  id: string;
  status: string;
  seasons: SeasonLike[];
  nextEpisodeAirAt?: unknown;
}

// Every season done, and nothing more on the way. The "+" button changes a
// season's watched count while the Episodes tab ticks individual episodes, so
// either one can show a season is finished. A season whose length is unknown
// cannot be called finished.
export function isFullyWatched(show: ShowLike): boolean {
  if (show.nextEpisodeAirAt || !show.seasons.length) return false;
  return show.seasons.every((season) => {
    const rows = season.episodes ?? [];
    const total = season.episodeCount ?? (rows.length || null);
    if (!total) return false;
    return (
      season.episodesWatched >= total ||
      (rows.length >= total && rows.every((e) => e.watched))
    );
  });
}

// asked once per show, until it is no longer fully watched
const declined = new Set<string>();

export function useCompletionPrompt() {
  const confirm = useConfirm();
  // true when the person wants it marked Completed
  return async function askToComplete(show: ShowLike): Promise<boolean> {
    if (!isFullyWatched(show)) {
      declined.delete(show.id);
      return false;
    }
    const bucket = statusBucket(show.status);
    if (bucket === "completed" || bucket === "dropped" || declined.has(show.id))
      return false;
    const yes = await confirm({
      message: "You've watched every episode. Move this to Completed?",
      confirmLabel: "Move to Completed",
      cancelLabel: "Leave as is",
    });
    if (!yes) declined.add(show.id);
    return yes;
  };
}
