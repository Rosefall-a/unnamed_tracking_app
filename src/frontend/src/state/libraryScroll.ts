// Remembers the Games tab's scroll position across a visit to a game's
// detail page and back. Captured from a router guard (before any DOM
// change happens) rather than the component's onUnmounted, by the time
// onUnmounted fires, the outgoing route's content may already have started
// shifting, so window.scrollY isn't reliably the position the user was
// actually looking at.
let savedScrollY = 0;

export function saveLibraryScroll(y: number): void {
  savedScrollY = y;
}

export function hasLibraryScroll(): boolean {
  return savedScrollY > 0;
}

export function takeLibraryScroll(): number {
  const y = savedScrollY;
  savedScrollY = 0;
  return y;
}

export function isGameDetailPath(path: string): boolean {
  return /^\/games\/[^/]+$/.test(path) && path !== "/games/collections";
}

export function captureLibraryNavigation(
  toPath: string,
  fromPath: string,
  scrollY: number,
): void {
  if (fromPath === "/games" && isGameDetailPath(toPath)) {
    saveLibraryScroll(scrollY);
  } else if (!isGameDetailPath(fromPath)) {
    saveLibraryScroll(0);
  }
}
