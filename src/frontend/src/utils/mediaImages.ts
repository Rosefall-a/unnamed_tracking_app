// A movie, show or anime stores the address of its poster and backdrop on
// TMDB or AniList. The server keeps a small local copy of each, so a page asks
// for that one and nothing waits on someone else's server.
export type MediaKind = "movie" | "tv" | "anime";

// "hero" is the picture behind a page's title: the backdrop, or the poster when
// there is no backdrop.
export type MediaImage = "poster" | "backdrop" | "hero";

// A short stamp of the original address, so changing it on the title gets a
// fresh picture instead of the one the browser remembered.
function stamp(text: string): string {
  let hash = 5381;
  for (let i = 0; i < text.length; i++)
    hash = ((hash << 5) + hash + text.charCodeAt(i)) | 0;
  return (hash >>> 0).toString(36);
}

export function localMediaImage(
  kind: MediaKind,
  id: string,
  which: MediaImage,
  remote: string | null | undefined,
): string | null {
  if (!remote) return null;
  if (!/^https?:\/\//i.test(remote)) return remote;
  return `/api/media-image/${kind}/${id}/${which}?v=${stamp(remote)}`;
}
