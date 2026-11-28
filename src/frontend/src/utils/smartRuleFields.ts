// What each smart rule asks for, shared by the rule editor in a smart
// collection and in a library tab: the kind of box, its hint, and its limits.
import { SMART_FIELD_LABELS } from "../state/smartCollections";
import type { SmartCondition, SmartField } from "../state/smartCollections";
import type { GameStatus } from "../types/game";

export const STATUS_OPTIONS: GameStatus[] = [
  "playing",
  "beaten",
  "mastered",
  "played",
  "on hold",
  "dropped",
  "backlog",
  "wishlist",
];

export const TEXT_FIELDS: Partial<Record<SmartField, string>> = {
  tag: "e.g. RPG",
  source: "e.g. Steam",
  platform: "e.g. PC",
  series: "e.g. Dark Souls",
  collection: "e.g. Online",
};

export const NUMBER_FIELDS: Partial<
  Record<SmartField, { min: number; max: number; hint: string }>
> = {
  playtime_hours: { min: 0, max: 100000, hint: "hours, e.g. 20" },
  achievement_percent: { min: 0, max: 100, hint: "%, e.g. 80" },
  priority: { min: 1, max: 5, hint: "1 to 5" },
  finished_year: { min: 1950, max: 2100, hint: "e.g. 2026" },
  released_from: { min: 1950, max: 2100, hint: "e.g. 2010" },
  released_to: { min: 1950, max: 2100, hint: "e.g. 2015" },
  added_within_days: { min: 1, max: 36500, hint: "days, e.g. 30" },
  played_within_days: { min: 1, max: 36500, hint: "days, e.g. 30" },
  not_played_days: { min: 1, max: 36500, hint: "days, e.g. 180" },
};

export interface RuleRow {
  field: SmartField;
  // a number box hands back a number, so either is read as text on save
  value: string | number;
  // "leave out" these games instead of keeping them
  not?: boolean;
}

// The rows as conditions, or what is wrong with them.
export function rowsToConditions(rows: RuleRow[]): SmartCondition[] | string {
  const out: SmartCondition[] = [];
  for (const row of rows) {
    const value = String(row.value ?? "").trim();
    const label = SMART_FIELD_LABELS[row.field];
    const not = row.not ? { not: true } : {};
    if (row.field === "favorite") {
      out.push({ field: "favorite", value: "", ...not });
      continue;
    }
    if (!value) return `Fill in "${label}".`;
    const limits = NUMBER_FIELDS[row.field];
    if (limits) {
      const n = Number(value);
      if (!Number.isFinite(n) || n < limits.min || n > limits.max)
        return `"${label}" needs a number from ${limits.min} to ${limits.max}.`;
    }
    out.push({ field: row.field, value, ...not });
  }
  return out.length ? out : "Add at least one rule.";
}
