// The Home page is pages of widgets placed on a 12 column grid. This file is the
// shape of that layout, the default one, and the rules for moving things around.
// Widgets stay where they are put: moving one only displaces the ones it lands on,
// pushing them down just far enough. Nothing slides up on its own; "tidy" does that
// when asked.

export const GRID_COLUMNS = 12;

export interface WidgetInstance {
  id: string;
  type: string;
  x: number;
  y: number;
  w: number;
  h: number;
  settings: Record<string, unknown>;
  variant: string | null;
}

export type PageGap = "tight" | "cozy" | "roomy";
export type PageBackdrop = "none" | "glow";

export interface PageOptions {
  gap: PageGap;
  backdrop: PageBackdrop;
}

export interface HomePage {
  id: string;
  name: string;
  options: PageOptions;
  widgets: WidgetInstance[];
}

export interface HomeLayout {
  version: number;
  pages: HomePage[];
}

export const LAYOUT_VERSION = 1;
export const GAP_PX: Record<PageGap, number> = {
  tight: 10,
  cozy: 16,
  roomy: 24,
};
export const ROW_PX = 56;

const DEFAULT_OPTIONS: PageOptions = { gap: "cozy", backdrop: "glow" };

function widget(
  type: string,
  x: number,
  y: number,
  w: number,
  h: number,
  settings: Record<string, unknown> = {},
  variant: string | null = null,
): WidgetInstance {
  return { id: `${type}-${x}-${y}`, type, x, y, w, h, settings, variant };
}

// What a new account sees, and what "Reset" goes back to. Every widget is one a
// person can remove; none are special.
export function defaultLayout(): HomeLayout {
  return {
    version: LAYOUT_VERSION,
    pages: [
      {
        id: "home",
        name: "Home",
        options: { ...DEFAULT_OPTIONS },
        widgets: [
          widget("greeting", 0, 0, 12, 2),
          widget("continue", 0, 2, 12, 4),
          widget("rail", 0, 6, 12, 4, { source: "recently-added" }),
          widget("achievements-recent", 0, 10, 4, 4),
          widget("stats", 4, 10, 4, 4),
          widget("random", 8, 10, 4, 4),
          widget("on-this-day", 0, 14, 12, 4),
        ],
      },
    ],
  };
}

function clampInt(value: unknown, low: number, high: number, fallback: number) {
  if (typeof value !== "number" || !Number.isFinite(value)) return fallback;
  return Math.min(high, Math.max(low, Math.round(value)));
}

function cleanWidget(raw: unknown): WidgetInstance | null {
  if (!raw || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  if (typeof r.id !== "string" || typeof r.type !== "string") return null;
  const w = clampInt(r.w, 1, GRID_COLUMNS, 4);
  return {
    id: r.id,
    type: r.type,
    x: clampInt(r.x, 0, GRID_COLUMNS - w, 0),
    y: clampInt(r.y, 0, 400, 0),
    w,
    h: clampInt(r.h, 1, 40, 3),
    settings:
      r.settings && typeof r.settings === "object"
        ? { ...(r.settings as Record<string, unknown>) }
        : {},
    variant: typeof r.variant === "string" ? r.variant : null,
  };
}

// A saved layout is read defensively: anything off about it falls back to the
// default instead of leaving Home blank.
export function normaliseLayout(raw: unknown): HomeLayout {
  if (!raw || typeof raw !== "object") return defaultLayout();
  const pages = (raw as { pages?: unknown }).pages;
  if (!Array.isArray(pages) || !pages.length) return defaultLayout();
  const clean: HomePage[] = [];
  for (const p of pages) {
    if (!p || typeof p !== "object") continue;
    const page = p as Record<string, unknown>;
    if (typeof page.id !== "string" || typeof page.name !== "string") continue;
    const opts = (page.options ?? {}) as Record<string, unknown>;
    const widgets = (Array.isArray(page.widgets) ? page.widgets : [])
      .map(cleanWidget)
      .filter((w): w is WidgetInstance => w !== null);
    clean.push({
      id: page.id,
      name: page.name,
      options: {
        gap: ["tight", "cozy", "roomy"].includes(opts.gap as string)
          ? (opts.gap as PageGap)
          : DEFAULT_OPTIONS.gap,
        backdrop: ["none", "glow"].includes(opts.backdrop as string)
          ? (opts.backdrop as PageBackdrop)
          : DEFAULT_OPTIONS.backdrop,
      },
      widgets: resolveOverlaps(widgets),
    });
  }
  return clean.length
    ? { version: LAYOUT_VERSION, pages: clean }
    : defaultLayout();
}

export function cloneLayout(layout: HomeLayout): HomeLayout {
  return JSON.parse(JSON.stringify(layout)) as HomeLayout;
}

interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export function overlaps(a: Rect, b: Rect): boolean {
  return (
    a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h
  );
}

// Clears overlaps by moving widgets down, and nothing else: a widget that does not
// sit on another one stays exactly where it is. `pinned` is the one being moved and
// never gives way; the others, top to bottom, drop below whatever they overlap.
export function resolveOverlaps(
  widgets: WidgetInstance[],
  pinned?: string,
): WidgetInstance[] {
  const placed: WidgetInstance[] = [];
  const pin = widgets.find((w) => w.id === pinned);
  if (pin) placed.push({ ...pin });
  const rest = widgets
    .filter((w) => w.id !== pinned)
    .map((w) => ({ ...w }))
    .sort((a, b) => a.y - b.y || a.x - b.x);
  for (const w of rest) {
    let moved = true;
    while (moved) {
      moved = false;
      for (const other of placed) {
        if (overlaps(w, other)) {
          w.y = other.y + other.h;
          moved = true;
        }
      }
    }
    placed.push(w);
  }
  const order = new Map(widgets.map((w, i) => [w.id, i]));
  return placed.sort((a, b) => order.get(a.id)! - order.get(b.id)!);
}

// Everything slides up until it meets something, so there are no holes in the
// page. This is "tidy up"; moving a widget does not do it.
export function settle(
  widgets: WidgetInstance[],
  pinned?: string,
): WidgetInstance[] {
  const placed: WidgetInstance[] = [];
  const pin = widgets.find((w) => w.id === pinned);
  if (pin) placed.push({ ...pin });
  const rest = widgets
    .filter((w) => w.id !== pinned)
    .map((w) => ({ ...w }))
    .sort((a, b) => a.y - b.y || a.x - b.x);
  for (const w of rest) {
    // down past anything it sits on top of, then up as far as it can go
    let moved = true;
    while (moved) {
      moved = false;
      for (const other of placed) {
        if (overlaps(w, other)) {
          w.y = other.y + other.h;
          moved = true;
        }
      }
    }
    while (
      w.y > 0 &&
      !placed.some((other) => overlaps({ ...w, y: w.y - 1 }, other))
    )
      w.y -= 1;
    placed.push(w);
  }
  const order = new Map(widgets.map((w, i) => [w.id, i]));
  return placed.sort((a, b) => order.get(a.id)! - order.get(b.id)!);
}

export function moveWidget(
  widgets: WidgetInstance[],
  id: string,
  rect: Rect,
): WidgetInstance[] {
  const w = Math.min(GRID_COLUMNS, Math.max(1, rect.w));
  const next = widgets.map((item) =>
    item.id === id
      ? {
          ...item,
          x: Math.min(GRID_COLUMNS - w, Math.max(0, rect.x)),
          y: Math.max(0, rect.y),
          w,
          h: Math.max(1, rect.h),
        }
      : item,
  );
  return resolveOverlaps(next, id);
}

export function bottomOf(widgets: WidgetInstance[]): number {
  return widgets.reduce((low, w) => Math.max(low, w.y + w.h), 0);
}

export function uniqueId(type: string, widgets: WidgetInstance[]): string {
  const taken = new Set(widgets.map((w) => w.id));
  let n = 1;
  while (taken.has(`${type}-${n}`)) n += 1;
  return `${type}-${n}`;
}

export function addWidget(
  widgets: WidgetInstance[],
  type: string,
  size: { w: number; h: number },
  settings: Record<string, unknown>,
  variant: string | null,
): WidgetInstance[] {
  return resolveOverlaps([
    ...widgets,
    {
      id: uniqueId(type, widgets),
      type,
      x: 0,
      y: bottomOf(widgets),
      w: size.w,
      h: size.h,
      settings,
      variant,
    },
  ]);
}
