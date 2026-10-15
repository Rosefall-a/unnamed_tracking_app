import { describe, expect, it } from "vitest";
import {
  addWidget,
  defaultLayout,
  moveWidget,
  normaliseLayout,
  overlaps,
  resolveOverlaps,
  settle,
} from "../home/layout";
import type { WidgetInstance } from "../home/layout";
import { WIDGETS } from "../home/registry";

function w(
  id: string,
  x: number,
  y: number,
  ww: number,
  h: number,
): WidgetInstance {
  return { id, type: "rail", x, y, w: ww, h, settings: {}, variant: null };
}

function noOverlaps(widgets: WidgetInstance[]) {
  for (let i = 0; i < widgets.length; i++)
    for (let j = i + 1; j < widgets.length; j++)
      expect(overlaps(widgets[i], widgets[j])).toBe(false);
}

describe("settle", () => {
  it("slides widgets up so the page has no holes", () => {
    const out = settle([w("a", 0, 5, 4, 2), w("b", 6, 9, 4, 2)]);
    expect(out.find((i) => i.id === "a")!.y).toBe(0);
    expect(out.find((i) => i.id === "b")!.y).toBe(0);
  });

  it("keeps widgets that share columns stacked", () => {
    const out = settle([w("a", 0, 0, 6, 3), w("b", 0, 7, 6, 2)]);
    expect(out.find((i) => i.id === "b")!.y).toBe(3);
  });

  it("never leaves two widgets overlapping", () => {
    noOverlaps(
      settle([w("a", 0, 0, 6, 3), w("b", 3, 1, 6, 3), w("c", 0, 2, 12, 2)]),
    );
  });
});

describe("moveWidget", () => {
  it("pushes what it lands on downward", () => {
    const start = [w("a", 0, 0, 6, 3), w("b", 6, 0, 6, 3)];
    const out = moveWidget(start, "a", { x: 6, y: 0, w: 6, h: 3 });
    expect(out.find((i) => i.id === "a")!.x).toBe(6);
    expect(out.find((i) => i.id === "b")!.y).toBe(3);
    noOverlaps(out);
  });

  it("keeps a widget inside the 12 columns", () => {
    const out = moveWidget([w("a", 0, 0, 6, 3)], "a", {
      x: 40,
      y: 0,
      w: 6,
      h: 3,
    });
    expect(out[0].x).toBe(6);
  });

  it("does not let a widget go above the page", () => {
    const out = moveWidget([w("a", 0, 4, 6, 3)], "a", {
      x: 0,
      y: -9,
      w: 6,
      h: 3,
    });
    expect(out[0].y).toBe(0);
  });
});

describe("addWidget", () => {
  it("puts a new widget at the bottom with its own id", () => {
    const start = [w("rail-1", 0, 0, 12, 4)];
    const out = addWidget(start, "rail", { w: 6, h: 3 }, { count: 5 }, "wide");
    const added = out.find((i) => i.id !== "rail-1")!;
    expect(added.id).toBe("rail-2");
    expect(added.y).toBe(4);
    expect(added.variant).toBe("wide");
    expect(added.settings).toEqual({ count: 5 });
  });
});

describe("normaliseLayout", () => {
  it("falls back to the default for anything unusable", () => {
    for (const bad of [null, 5, "x", {}, { pages: [] }, { pages: [{}] }])
      expect(normaliseLayout(bad).pages.length).toBeGreaterThan(0);
  });

  it("clamps sizes and drops entries that are not widgets", () => {
    const layout = normaliseLayout({
      pages: [
        {
          id: "p",
          name: "P",
          options: { gap: "huge", backdrop: "none" },
          widgets: [
            {
              id: "a",
              type: "rail",
              x: 99,
              y: -3,
              w: 99,
              h: 0,
              settings: null,
            },
            "nonsense",
            { id: 4 },
          ],
        },
      ],
    });
    const page = layout.pages[0];
    expect(page.options).toEqual({ gap: "cozy", backdrop: "none" });
    expect(page.widgets).toHaveLength(1);
    expect(page.widgets[0]).toMatchObject({
      x: 0,
      y: 0,
      w: 12,
      h: 1,
      settings: {},
    });
  });

  it("keeps a widget it has no definition for, so the page can say so", () => {
    const layout = normaliseLayout({
      pages: [
        {
          id: "p",
          name: "P",
          options: {},
          widgets: [
            { id: "a", type: "removed-plugin", x: 0, y: 0, w: 4, h: 3 },
          ],
        },
      ],
    });
    expect(layout.pages[0].widgets[0].type).toBe("removed-plugin");
  });
});

describe("default layout", () => {
  const layout = defaultLayout();

  it("only uses widgets that exist", () => {
    const known = new Set(WIDGETS.map((d) => d.type));
    for (const item of layout.pages[0].widgets)
      expect(known.has(item.type)).toBe(true);
  });

  it("has no overlaps and stays inside the grid", () => {
    noOverlaps(layout.pages[0].widgets);
    for (const item of layout.pages[0].widgets)
      expect(item.x + item.w).toBeLessThanOrEqual(12);
  });

  it("survives being normalised unchanged", () => {
    expect(normaliseLayout(layout)).toEqual(layout);
  });
});

describe("widget registry", () => {
  it("has unique types and sensible sizes", () => {
    const types = WIDGETS.map((d) => d.type);
    expect(new Set(types).size).toBe(types.length);
    for (const d of WIDGETS) {
      expect(d.size.minW).toBeLessThanOrEqual(d.size.w);
      expect(d.size.minH).toBeLessThanOrEqual(d.size.h);
      expect(d.size.w).toBeLessThanOrEqual(12);
    }
  });

  it("gives every setting a default", () => {
    for (const d of WIDGETS)
      for (const f of d.fields) expect(d.defaults).toHaveProperty(f.key);
  });
});

describe("moving leaves the rest of the page alone", () => {
  const start = [w("a", 0, 0, 6, 3), w("b", 6, 0, 6, 3), w("c", 0, 10, 12, 2)];

  it("only displaces what it lands on", () => {
    const out = moveWidget(start, "a", { x: 6, y: 0, w: 6, h: 3 });
    expect(out.find((i) => i.id === "b")!.y).toBe(3);
    expect(out.find((i) => i.id === "c")).toMatchObject({ x: 0, y: 10 });
  });

  it("does not pull anything up into the space it left", () => {
    const out = moveWidget(start, "a", { x: 0, y: 6, w: 6, h: 3 });
    expect(out.find((i) => i.id === "b")).toMatchObject({ x: 6, y: 0 });
    expect(out.find((i) => i.id === "c")).toMatchObject({ x: 0, y: 10 });
  });

  it("brings a displaced widget back when worked out from the start again", () => {
    const over = moveWidget(start, "a", { x: 6, y: 0, w: 6, h: 3 });
    expect(over.find((i) => i.id === "b")!.y).toBe(3);
    const off = moveWidget(start, "a", { x: 0, y: 6, w: 6, h: 3 });
    expect(off.find((i) => i.id === "b")!.y).toBe(0);
  });

  it("cascades only as far as it has to", () => {
    const stack = [w("a", 0, 0, 6, 3), w("b", 0, 3, 6, 3), w("c", 0, 12, 6, 3)];
    const out = moveWidget(stack, "c", { x: 0, y: 0, w: 6, h: 3 });
    expect(out.find((i) => i.id === "a")!.y).toBe(3);
    expect(out.find((i) => i.id === "b")!.y).toBe(6);
  });

  it("tidy up, and only that, closes the gaps", () => {
    const gappy = [w("a", 0, 0, 6, 3), w("b", 0, 9, 6, 3)];
    expect(resolveOverlaps(gappy)[1].y).toBe(9);
    expect(settle(gappy)[1].y).toBe(3);
  });
});
