import { describe, expect, it } from "vitest";
import { numberOrNull } from "../utils/numberInput";

describe("numberOrNull", () => {
  it("turns an emptied box into null", () => {
    expect(numberOrNull("")).toBeNull();
    expect(numberOrNull(null)).toBeNull();
    expect(numberOrNull(undefined)).toBeNull();
  });
  it("keeps a real number, zero included", () => {
    expect(numberOrNull(0)).toBe(0);
    expect(numberOrNull(7.5)).toBe(7.5);
    expect(numberOrNull("8")).toBe(8);
  });
  it("drops what is not a number", () => {
    expect(numberOrNull(Number.NaN)).toBeNull();
    expect(numberOrNull("abc")).toBeNull();
  });
});
