export const GENRE_OPTIONS = [
  "Action",
  "Adventure",
  "RPG",
  "Shooter",
  "Platformer",
  "Puzzle",
  "Strategy",
  "Simulation",
  "Sports",
  "Racing",
  "Fighting",
  "Horror",
  "Survival",
  "Stealth",
  "Sandbox",
  "Open World",
  "Metroidvania",
  "Roguelike",
  "Rhythm",
  "Visual Novel",
  "Party",
  "Card & Board",
  "MMO",
  "Tactics",
  "Educational",
];

// Game tags are stored as each metadata provider named them, and the
// providers disagree: IGDB has no "Action" genre at all (Devil May Cry is
// "Hack and slash/Beat 'em up") and says "Role-playing (RPG)" and
// "Platform" where the list above says "RPG" and "Platformer". Filters match
// through these aliases so a genre finds the same games whichever provider
// described them. Keys are lower-case letters and digits only.
const GENRE_ALIASES: Record<string, string[]> = {
  hackandslashbeatemup: ["Action"],
  hackandslash: ["Action"],
  beatemup: ["Action"],
  brawler: ["Action"],
  actionadventure: ["Action", "Adventure"],
  actionrpg: ["Action", "RPG"],
  shooter: ["Action"],
  firstpersonshooter: ["Shooter", "Action"],
  thirdpersonshooter: ["Shooter", "Action"],
  fighting: ["Action"],
  platform: ["Platformer"],
  roleplaying: ["RPG"],
  roleplayingrpg: ["RPG"],
  realtimestrategy: ["Strategy"],
  realtimestrategyrts: ["Strategy"],
  turnbasedstrategy: ["Strategy"],
  turnbasedstrategytbs: ["Strategy"],
  tactical: ["Tactics"],
  simulator: ["Simulation"],
  sport: ["Sports"],
  drivingracing: ["Racing"],
  music: ["Rhythm"],
  musicrhythm: ["Rhythm"],
  cardboardgame: ["Card & Board"],
  cardgame: ["Card & Board"],
  boardgame: ["Card & Board"],
  massivelymultiplayer: ["MMO"],
  mmorpg: ["MMO", "RPG"],
  survivalhorror: ["Survival", "Horror"],
};

function genreKey(genre: string): string {
  return genre.toLowerCase().replace(/[^a-z0-9]/g, "");
}

const GENRE_BY_KEY = new Map(GENRE_OPTIONS.map((g) => [genreKey(g), g]));

// Every genre a game's tags stand for: each tag itself (spelled like the
// shared list when it is one of those, so "action" reads "Action") plus the
// shared genres it maps to, without duplicates.
export function gameGenres(tags: string[]): string[] {
  const byKey = new Map<string, string>();
  const add = (genre: string) => {
    const key = genreKey(genre);
    if (key && !byKey.has(key))
      byKey.set(key, GENRE_BY_KEY.get(key) ?? genre.trim());
  };
  for (const tag of tags) {
    add(tag);
    (GENRE_ALIASES[genreKey(tag)] ?? []).forEach(add);
  }
  return [...byKey.values()];
}

export function hasGenre(tags: string[], genre: string): boolean {
  const key = genreKey(genre);
  return gameGenres(tags).some((g) => genreKey(g) === key);
}

// Filter choices: the shared genres plus every genre found in the library.
export function genreOptionsFor(tagLists: string[][]): string[] {
  return gameGenres([...GENRE_OPTIONS, ...tagLists.flat()]).sort();
}
