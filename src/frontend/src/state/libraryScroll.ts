// Remembers the Games tab's scroll position across a visit to a game's
// detail page and back. Captured from a router guard (before any DOM
// change happens) rather than the component's onUnmounted, by the time
// onUnmounted fires, the outgoing route's content may already have started
// shifting, so window.scrollY isn't reliably the position the user was
// actually looking at.
let savedScrollY = 0

export function saveLibraryScroll(y: number): void {
  savedScrollY = y
}

export function takeLibraryScroll(): number {
  return savedScrollY
}
