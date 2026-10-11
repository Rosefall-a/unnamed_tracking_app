// A game's cover and banner are replaced in place, under the same address. A page
// that is already showing the old picture does not ask for it again, so each
// replacement here gives that game's art addresses a new `v=` value, and the next
// time the game is read the page loads the new picture. Held only for this visit: on
// a fresh load the server is asked, and it answers "not modified" or sends the new
// file.
const versions = new Map<string, number>();

export function bumpArt(gameId: string): void {
  versions.set(gameId, Date.now());
}

export function withArtVersion(url: string, gameId: string): string {
  const version = versions.get(gameId);
  return version === undefined ? url : `${url}?v=${version}`;
}
