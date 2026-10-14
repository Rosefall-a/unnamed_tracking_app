import { describe, expect, it } from "vitest";

import {
  formatDuration,
  formatProgressMinutes,
  parseProgressMinutes,
  progressPercent,
} from "../utils/watchProgress";

describe("movie left-off point (#191)", () => {
  it("accepts minutes or h:mm", () => {
    expect(parseProgressMinutes("72")).toBe(72);
    expect(parseProgressMinutes("1:12")).toBe(72);
    expect(parseProgressMinutes(" 0:05 ")).toBe(5);
    expect(parseProgressMinutes("")).toBeNull();
    expect(parseProgressMinutes("an hour")).toBeNaN();
    expect(parseProgressMinutes("1:75")).toBeNaN();
  });

  it("formats as h:mm", () => {
    expect(formatProgressMinutes(72)).toBe("1:12");
    expect(formatProgressMinutes(5)).toBe("0:05");
    expect(formatProgressMinutes(parseProgressMinutes("2:28")!)).toBe("2:28");
  });

  it("reports progress against the runtime, capped at 100%", () => {
    expect(progressPercent(74, 148)).toBe(50);
    expect(progressPercent(200, 148)).toBe(100);
    expect(progressPercent(30, null)).toBeNull();
    expect(progressPercent(null, 148)).toBeNull();
  });
});

describe("friendlier times", () => {
  it("reads hours and minutes written out", () => {
    expect(parseProgressMinutes("1h 12m")).toBe(72);
    expect(parseProgressMinutes("1h12")).toBe(72);
    expect(parseProgressMinutes("2h")).toBe(120);
    expect(parseProgressMinutes("45m")).toBe(45);
    expect(parseProgressMinutes("1.5h")).toBe(90);
    expect(parseProgressMinutes("1h 75m")).toBeNaN();
  });
  it("shows hours and minutes", () => {
    expect(formatDuration(105)).toBe("1h 45m");
    expect(formatDuration(120)).toBe("2h");
    expect(formatDuration(45)).toBe("45m");
  });
});
