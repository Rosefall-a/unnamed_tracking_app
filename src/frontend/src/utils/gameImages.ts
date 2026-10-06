// Artwork for a game comes from /api/game/<id>/assets/<kind>. A banner is a
// 3840 px PNG of several MB, so a page asks for a copy no wider than it shows.
export function sizedAssetUrl(url: string, width: number): string {
  // already sized, or not one of ours
  if (!url.startsWith("/api/") || /[?&]w=/.test(url)) return url;
  return `${url}${url.includes("?") ? "&" : "?"}w=${width}`;
}

// The hero is about as wide as a big screen, so this is plenty for it.
export const HERO_WIDTH = 1920;
// The poster is 190 px wide on the page; twice that keeps it sharp on a retina screen.
export const POSTER_WIDTH = 400;

// Starts downloading an image so it is already there when the page asks.
export function preloadImage(url: string): void {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") return;
  const image = new Image();
  image.src = url;
}
