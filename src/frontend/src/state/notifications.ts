// Episode/season/movie notifications from the server: the app's one
// notification source. Persisted server-side, so they can be read/unread.
import { ref } from "vue";
import {
  fetchMediaNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../services/notifications";
import type { MediaNotification } from "../services/notifications";

export const mediaNotifications = ref<MediaNotification[]>([]);
export const mediaUnread = ref(0);

let lastFetchedAt = 0;
let inFlight: Promise<void> | null = null;

// With `maxAgeMs`, a list fetched that recently is kept, and a request
// already on its way is shared: every page change mounts a new bell, which
// asked the server again each time (and, at startup, alongside the sidebar).
// Without it the list is always fetched, as after marking or deleting.
export async function refreshMediaNotifications(
  options: { maxAgeMs?: number } = {},
): Promise<void> {
  if (options.maxAgeMs) {
    if (Date.now() - lastFetchedAt < options.maxAgeMs) return;
    if (inFlight) return inFlight;
  }
  const request = (async () => {
    try {
      const res = await fetchMediaNotifications();
      mediaNotifications.value = res.items;
      mediaUnread.value = res.unread;
      lastFetchedAt = Date.now();
    } catch {
      // the badge simply doesn't change this tick
    }
  })();
  inFlight = request;
  try {
    await request;
  } finally {
    if (inFlight === request) inFlight = null;
  }
}

export async function readMediaNotification(id: string) {
  const n = mediaNotifications.value.find((m) => m.id === id);
  if (!n || n.read) return;
  n.read = true;
  mediaUnread.value = Math.max(0, mediaUnread.value - 1);
  try {
    await markNotificationRead(id);
  } catch {
    n.read = false;
    mediaUnread.value += 1;
  }
}

export async function readAllMediaNotifications() {
  const before = mediaNotifications.value.map((n) => n.read);
  mediaNotifications.value.forEach((n) => (n.read = true));
  const unread = mediaUnread.value;
  mediaUnread.value = 0;
  try {
    await markAllNotificationsRead();
  } catch {
    mediaNotifications.value.forEach((n, i) => (n.read = before[i]));
    mediaUnread.value = unread;
  }
}

export function mediaNotificationRoute(n: MediaNotification): string {
  const base =
    n.mediaType === "movie"
      ? "/movies"
      : n.mediaType === "tv"
        ? "/tv"
        : "/anime";
  return `${base}/${n.mediaId}`;
}
