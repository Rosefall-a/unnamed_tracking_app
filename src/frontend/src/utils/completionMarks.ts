// The ways a 100% game can be marked on library covers. Any mix can be on.
import { computed } from "vue";
import { preferences } from "../state/preferences";
import { appearanceSettings } from "../state/appearance";
import type { BadgeStyle } from "../services/appearanceSettings";

export type CompletionMark =
  "caption" | "seal" | "gold_title" | "sheen" | "rarest_pin";

export const MARKS: { id: CompletionMark; label: string; hint: string }[] = [
  {
    id: "caption",
    label: "Caption",
    hint: "A gold trophy and 100% under the title",
  },
  {
    id: "seal",
    label: "Seal",
    hint: "A small frosted circle with a trophy in the corner",
  },
  {
    id: "gold_title",
    label: "Gold title",
    hint: "The name turns gold with a trophy by the count",
  },
  {
    id: "sheen",
    label: "Foil sheen",
    hint: "A shine sweeps across on hover",
  },
  {
    id: "rarest_pin",
    label: "Rarest pin",
    hint: "Your rarest unlock's icon and % in the corner",
  },
];

// what the older single "badge style" setting becomes, so nobody's look
// changes until they pick marks themselves
export function marksFromBadgeStyle(
  style: BadgeStyle | undefined,
): CompletionMark[] {
  if (style === "glow" || style === "border") return ["caption"];
  if (style === "ribbon" || style === "corner_badge") return ["seal"];
  if (style === "none") return [];
  return ["caption", "seal"];
}

const KNOWN = new Set<string>(MARKS.map((m) => m.id));

// a mark saved before it was taken out of the list is simply not shown
export const activeMarks = computed<Set<CompletionMark>>(
  () =>
    new Set(
      (
        preferences.value.completion_marks ??
        marksFromBadgeStyle(appearanceSettings.value?.completion_badge_style)
      ).filter((m) => KNOWN.has(m)),
    ),
);
