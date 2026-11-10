import { describe, expect, it } from "vitest";
import { pickResult, titleWithYear } from "../utils/mediaLookup";

const results = [
  { providerId: "tt3201640", title: "Extinction", year: "2018" },
  { providerId: "tt3467412", title: "Extinction", year: "2015" },
  {
    providerId: "tt2109248",
    title: "Transformers: Age of Extinction",
    year: "2014",
  },
];

describe("picking the search result someone chose", () => {
  it("finds it by the provider's id, not just the title", () => {
    expect(
      pickResult(results, { title: "Extinction", providerId: "tt3467412" })
        ?.year,
    ).toBe("2015");
  });

  it("without an id, the year tells same-named titles apart", () => {
    expect(
      pickResult(results, { title: "Extinction", year: "2015" })?.providerId,
    ).toBe("tt3467412");
  });

  it("searches with the year after the title when there is one", () => {
    expect(titleWithYear("Extinction", "2015")).toBe("Extinction 2015");
    expect(titleWithYear("Extinction", null)).toBe("Extinction");
  });
});
