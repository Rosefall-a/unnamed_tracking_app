// Syncing a library files each game into a collection named after its series
// and one named after where it came from (Steam), so a collection can be
// something the app made, not something you did. Those are told apart here: a
// collection is automatic when every game in it is in it because of its series or
// its source.
import type { Game } from "../types/game";

const same = (a: string | null | undefined, b: string) =>
  !!a && a.trim().toLowerCase() === b.trim().toLowerCase();

export function autoCollectionNames(games: Game[]): Set<string> {
  const members = new Map<string, Game[]>();
  for (const g of games)
    for (const name of g.collections) {
      const list = members.get(name);
      if (list) list.push(g);
      else members.set(name, [g]);
    }
  const auto = new Set<string>();
  for (const [name, list] of members)
    if (list.every((g) => same(g.series, name) || same(g.source, name)))
      auto.add(name);
  return auto;
}
