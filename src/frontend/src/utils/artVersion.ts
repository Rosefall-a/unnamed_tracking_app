// A game's cover and banner are replaced in place, under the same address, and the
// browser keeps what it has fetched for an hour or more. Each replacement gives that
// game's art addresses a new `v=` value: an address the browser has never seen is
// fetched fresh, so the new picture shows at once, and it is then kept like any other.
// The value is stored in this browser so it holds after a reload; losing it (cleared
// site data) only means the old copy shows until its hour is up.
const KEY = "gameArtVersions";

function load(): Map<string, number> {
  try {
    const raw = localStorage.getItem(KEY);
    return new Map(Object.entries(raw ? JSON.parse(raw) : {}));
  } catch {
    return new Map();
  }
}

const versions = load();

export function bumpArt(gameId: string): void {
  versions.set(gameId, Date.now());
  try {
    localStorage.setItem(KEY, JSON.stringify(Object.fromEntries(versions)));
  } catch {
    // kept for this visit only
  }
}

export function withArtVersion(url: string, gameId: string): string {
  const version = versions.get(gameId);
  return version === undefined ? url : `${url}?v=${version}`;
}
