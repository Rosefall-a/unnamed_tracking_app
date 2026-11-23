// Rule-based ("smart") collections, membership is computed live against
// whatever the library looks like right now, instead of being a stored
// list of game ids. Rules are saved on the server with the person's other
// page choices (state/uiState.ts), like manual collections.
import { computed } from "vue";
import { getUi, setUi } from "./uiState";
import type { Game } from "../types/game";

export type SmartField =
  | "status"
  | "playtime_hours"
  | "favorite"
  | "tag"
  | "source"
  | "achievement_percent"
  | "platform"
  | "series"
  | "priority"
  | "finished_year"
  | "released_from"
  | "released_to"
  | "added_within_days"
  | "played_within_days"
  | "not_played_days";

// one condition: unused value for 'favorite'; a GameStatus value for 'status';
// free text for 'tag', 'source', 'platform' and 'series'; a number as text
// for the rest (hours, a percentage, a year, a count of days, a priority)
export interface SmartCondition {
  field: SmartField;
  value: string;
}

export type SmartMatch = "all" | "any";

export interface SmartCollection extends SmartCondition {
  id: string;
  name: string;
  // more than one condition; when set, `field` and `value` are its first one
  // (kept so a rule saved before this still reads the same)
  rules?: SmartCondition[];
  // every condition must match, or any one of them
  match?: SmartMatch;
}

// what the form edits and saves
export interface SmartDefinition extends SmartCondition {
  rules: SmartCondition[];
  match: SmartMatch;
}

const STORAGE_KEY = "smartCollections";

export const smartCollections = computed<SmartCollection[]>({
  get: () => {
    const saved = getUi<unknown>(STORAGE_KEY, []);
    return Array.isArray(saved) ? (saved as SmartCollection[]) : [];
  },
  set: (list) => setUi(STORAGE_KEY, list),
});

// The one collection the app keeps itself, like Media's Favorites list: every
// game you have favorited, filled by a rule nobody can edit or delete. It is
// not stored with the user's own rules; a collection of the user's with the
// same name takes its place.
export const FAVORITES_NAME = "Favorites";
export const FAVORITES_RULE: SmartCollection = {
  id: "system-favorites",
  name: FAVORITES_NAME,
  field: "favorite",
  value: "",
};

export function conditionsOf(rule: SmartCollection): SmartCondition[] {
  return rule.rules?.length
    ? rule.rules
    : [{ field: rule.field, value: rule.value }];
}

export function definitionOf(rule: SmartCollection): SmartDefinition {
  return {
    field: rule.field,
    value: rule.value,
    rules: conditionsOf(rule).map((c) => ({ ...c })),
    match: rule.match ?? "all",
  };
}

export function addSmartCollection(entry: Omit<SmartCollection, "id">): string {
  const id = crypto.randomUUID();
  smartCollections.value = [...smartCollections.value, { ...entry, id }];
  return id;
}

export function updateSmartCollection(
  id: string,
  patch: Partial<Omit<SmartCollection, "id">>,
) {
  smartCollections.value = smartCollections.value.map((c) =>
    c.id === id ? { ...c, ...patch } : c,
  );
}

export function removeSmartCollection(id: string) {
  smartCollections.value = smartCollections.value.filter((c) => c.id !== id);
}

export function findSmartCollectionByName(
  name: string,
): SmartCollection | undefined {
  return smartCollections.value.find((c) => c.name === name);
}

const DAY_MS = 86_400_000;

function lastPlayed(game: Game): number | null {
  const times = [
    game.lastPlayedAt,
    ...game.platforms.map((p) => p.lastPlayedAt),
  ]
    .filter((d): d is string => !!d)
    .map((d) => Date.parse(d))
    .filter((t) => !Number.isNaN(t));
  return times.length ? Math.max(...times) : null;
}

function yearOf(value: string | null | undefined): number | null {
  const year = Number((value ?? "").slice(0, 4));
  return value && year > 0 ? year : null;
}

function same(a: string | null | undefined, b: string): boolean {
  return (a ?? "").trim().toLowerCase() === b.trim().toLowerCase();
}

export function matchesCondition(
  game: Game,
  rule: SmartCondition,
  now = Date.now(),
): boolean {
  const n = Number(rule.value);
  switch (rule.field) {
    case "status":
      return game.status === rule.value;
    case "favorite":
      return game.favorite === true;
    case "source":
      return same(game.source, rule.value);
    case "tag":
      return game.tags.some((t) => same(t, rule.value));
    case "platform":
      return (
        same(game.platform, rule.value) ||
        game.platforms.some((p) => same(p.platform, rule.value))
      );
    case "series":
      return same(game.series, rule.value);
    // 1 is the highest, so "priority 2" means 1 or 2
    case "priority": {
      const p = Number(game.priority);
      return game.priority != null && p > 0 && p <= n;
    }
    case "playtime_hours": {
      const totalMinutes = game.platforms.reduce(
        (sum, p) => sum + p.playtimeMinutes,
        0,
      );
      return totalMinutes / 60 > n;
    }
    // at least this share unlocked, with some still to get: "almost there"
    case "achievement_percent": {
      const unlocked = game.achievementUnlocked ?? 0;
      if (!game.achievementTotal || unlocked >= game.achievementTotal)
        return false;
      return (unlocked / game.achievementTotal) * 100 >= n;
    }
    case "finished_year":
      return yearOf(game.completionDate) === n;
    case "released_from": {
      const year = yearOf(game.releaseDate);
      return year !== null && year >= n;
    }
    case "released_to": {
      const year = yearOf(game.releaseDate);
      return year !== null && year <= n;
    }
    case "added_within_days": {
      const added = Date.parse(game.dateAdded ?? "");
      return !Number.isNaN(added) && added >= now - n * DAY_MS;
    }
    case "played_within_days": {
      const at = lastPlayed(game);
      return at !== null && at >= now - n * DAY_MS;
    }
    // never played counts too: it has not been played in that time either
    case "not_played_days": {
      const at = lastPlayed(game);
      return at === null || at < now - n * DAY_MS;
    }
    default:
      return false;
  }
}

export function matchesSmartCollection(
  game: Game,
  rule: SmartCollection,
): boolean {
  const conditions = conditionsOf(rule);
  const now = Date.now();
  return rule.match === "any"
    ? conditions.some((c) => matchesCondition(game, c, now))
    : conditions.every((c) => matchesCondition(game, c, now));
}

export const SMART_FIELD_LABELS: Record<SmartField, string> = {
  status: "Status is",
  playtime_hours: "Playtime over (hours)",
  favorite: "Favorited",
  tag: "Tag is",
  source: "Source is",
  platform: "Platform is",
  series: "Series is",
  priority: "Priority at least (1 is highest)",
  achievement_percent: "Achievements unlocked, at least (%)",
  finished_year: "Finished in (year)",
  released_from: "Released in or after (year)",
  released_to: "Released in or before (year)",
  added_within_days: "Added in the last (days)",
  played_within_days: "Played in the last (days)",
  not_played_days: "Not played in the last (days)",
};

export function describeCondition(rule: SmartCondition): string {
  const v = rule.value;
  switch (rule.field) {
    case "favorite":
      return "Favorited";
    case "playtime_hours":
      return `Playtime over ${v}h`;
    case "achievement_percent":
      return `${v}% or more of achievements, not all yet`;
    case "priority":
      return `Priority ${v} or higher`;
    case "finished_year":
      return `Finished in ${v}`;
    case "released_from":
      return `Released in ${v} or later`;
    case "released_to":
      return `Released in ${v} or earlier`;
    case "added_within_days":
      return `Added in the last ${v} days`;
    case "played_within_days":
      return `Played in the last ${v} days`;
    case "not_played_days":
      return `Not played in the last ${v} days`;
    default:
      return `${SMART_FIELD_LABELS[rule.field]} "${v}"`;
  }
}

export function describeSmartCollection(rule: SmartCollection): string {
  return conditionsOf(rule)
    .map(describeCondition)
    .join(rule.match === "any" ? ", or " : ", and ");
}
