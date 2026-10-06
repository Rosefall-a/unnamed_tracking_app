import type { MediaNotification } from "../services/notifications";

type NotificationGroup = "episodes" | "seasons" | "releases" | "plugins";
type Presentation = {
  label: string;
  tone: string;
  group: NotificationGroup | null;
};
const kinds: Record<string, Presentation> = {
  episode_aired: { label: "Episode aired", tone: "amber", group: "episodes" },
  season_started: { label: "Season started", tone: "green", group: "seasons" },
  sequel_announced: {
    label: "New season listed",
    tone: "blue",
    group: "seasons",
  },
  movie_released: {
    label: "Movie released",
    tone: "violet",
    group: "releases",
  },
  plugin: { label: "Plugin", tone: "violet", group: "plugins" },
};
const fallback: Presentation = {
  label: "Notification",
  tone: "blue",
  group: null,
};

export function notificationPresentation(kind: string): Presentation {
  return Object.hasOwn(kinds, kind) ? kinds[kind]! : fallback;
}

export function notificationDestination(
  n: Pick<MediaNotification, "mediaType" | "mediaId">,
): string | null {
  if (!n.mediaId) return null;
  const roots: Record<string, string> = {
    movie: "/movies",
    tv: "/tv",
    anime: "/anime",
  };
  return Object.hasOwn(roots, n.mediaType)
    ? `${roots[n.mediaType]}/${encodeURIComponent(n.mediaId)}`
    : null;
}
