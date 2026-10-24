// Ready-made pages, so a new page does not have to be built widget by widget.
// Each is an ordinary page once added: every widget can be moved or removed.
import { resolveOverlaps, uniqueId } from "./layout";
import type { HomeLayout, HomePage, WidgetInstance } from "./layout";

type Placed = [
  type: string,
  x: number,
  y: number,
  w: number,
  h: number,
  settings?: Record<string, unknown>,
];

export interface StarterPage {
  id: string;
  name: string;
  description: string;
  widgets: Placed[];
}

const GAMES = ["game"];
const WATCHING = ["movie", "tv", "anime"];

export const STARTER_PAGES: StarterPage[] = [
  {
    id: "gaming",
    name: "Gaming",
    description:
      "What you are playing, your backlog, achievements and time played.",
    widgets: [
      ["continue", 0, 0, 12, 4, { kinds: GAMES }],
      ["rail", 0, 4, 12, 4, { source: "backlog", kinds: GAMES }],
      ["achievements-recent", 0, 8, 4, 4],
      ["most-played", 4, 8, 4, 4],
      ["backlog-time", 8, 8, 4, 4],
      ["random", 0, 12, 6, 5, { kinds: GAMES }],
    ],
  },
  {
    id: "watching",
    name: "Watching",
    description:
      "What airs next, where you are in each show, and what is out soon.",
    widgets: [
      ["up-next", 0, 0, 6, 5],
      ["next-episodes", 6, 0, 6, 5],
      ["continue", 0, 5, 12, 4, { kinds: WATCHING }],
      ["schedule", 0, 9, 12, 5],
      ["rail", 0, 14, 12, 4, { source: "backlog", kinds: WATCHING }],
    ],
  },
  {
    id: "overview",
    name: "Overview",
    description:
      "Your whole library in numbers: counts, genres, ratings and gaps.",
    widgets: [
      ["stats", 0, 0, 4, 4],
      ["breakdown", 4, 0, 4, 4],
      ["ratings", 8, 0, 4, 4],
      ["health", 0, 4, 4, 4],
      ["on-this-day", 4, 4, 8, 4],
    ],
  },
];

/** A new page made from a starter, with a page id and widget ids that no
 * other page in `layout` uses. */
export function starterPage(
  starter: StarterPage,
  layout: HomeLayout,
): HomePage {
  const taken = layout.pages.flatMap((p) => p.widgets.map((w) => w.id));
  const widgets: WidgetInstance[] = [];
  for (const [type, x, y, w, h, settings] of starter.widgets) {
    const id = uniqueId(type, taken);
    taken.push(id);
    widgets.push({
      id,
      type,
      x,
      y,
      w,
      h,
      settings: { ...settings },
      variant: null,
    });
  }
  let n = layout.pages.length + 1;
  while (layout.pages.some((p) => p.id === `page-${n}`)) n += 1;
  return {
    id: `page-${n}`,
    name: starter.name,
    options: { gap: "cozy", backdrop: "glow" },
    widgets: resolveOverlaps(widgets),
  };
}
