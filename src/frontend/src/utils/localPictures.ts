// Pictures and clips inside a game's description, and episode stills, come
// from this server's own copy so the page shows with no internet. The server
// keeps one copy of a clip Steam gives as webm and mp4 (the mp4, which every
// browser plays), and the page picks the same one (backend helpers/local_copies.py).

function online(url: string | null | undefined): url is string {
  return !!url && /^https?:\/\//i.test(url);
}

export function localEpisodeStill(
  kind: "tv" | "anime",
  id: string,
  remote: string | null | undefined,
): string | null {
  if (!remote) return null;
  if (!online(remote)) return remote;
  return `/api/episode-still/${kind}/${encodeURIComponent(id)}`;
}

function pageFile(gameId: string, url: string): string {
  return `/api/game/${encodeURIComponent(gameId)}/page-file?u=${encodeURIComponent(url)}`;
}

// `html` must already be sanitized; this only changes addresses.
export function withLocalPictures(html: string, gameId: string): string {
  if (!html || !/https?:\/\//i.test(html)) return html;
  const doc = new DOMParser().parseFromString(html, "text/html");
  for (const img of Array.from(doc.querySelectorAll("img"))) {
    const src = img.getAttribute("src");
    // a srcset would let the browser pick an online copy instead
    img.removeAttribute("srcset");
    if (online(src)) img.setAttribute("src", pageFile(gameId, src));
  }
  for (const video of Array.from(doc.querySelectorAll("video"))) {
    const poster = video.getAttribute("poster");
    if (online(poster)) video.setAttribute("poster", pageFile(gameId, poster));
    const sources = Array.from(video.querySelectorAll("source"));
    const isMp4 = (s: Element) =>
      /\.mp4$/i.test(new URL(s.getAttribute("src") ?? "", "http://x").pathname);
    const keep = sources.find(isMp4) ?? sources[0];
    for (const source of sources) {
      if (source !== keep) {
        source.remove();
        continue;
      }
      const src = source.getAttribute("src");
      if (online(src)) source.setAttribute("src", pageFile(gameId, src));
    }
  }
  return doc.body.innerHTML;
}
