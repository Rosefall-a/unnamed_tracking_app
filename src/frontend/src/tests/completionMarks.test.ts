import { describe, expect, it } from "vitest";
import { MARKS, marksFromBadgeStyle } from "../utils/completionMarks";

describe("100% cover marks", () => {
  it("keeps the look someone already had until they pick marks", () => {
    expect(marksFromBadgeStyle("border")).toEqual(["caption"]);
    expect(marksFromBadgeStyle("glow")).toEqual(["caption"]);
    expect(marksFromBadgeStyle("ribbon")).toEqual(["seal"]);
    expect(marksFromBadgeStyle("corner_badge")).toEqual(["seal"]);
    expect(marksFromBadgeStyle("none")).toEqual([]);
  });

  it("lists each mark once, with the same ids the server accepts", () => {
    const ids = MARKS.map((m) => m.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids).toEqual([
      "caption",
      "seal",
      "gold_title",
      "sheen",
      "rarest_pin",
    ]);
  });
});
