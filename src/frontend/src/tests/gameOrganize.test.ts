import { describe, expect, it } from "vitest";
import { isSetAside, reasonLabel } from "../utils/gameOrganize";
import { sameTitle } from "../utils/mediaDuplicates";

describe("set aside", () => {
  it("is set aside only when it has a date", () => {
    expect(isSetAside({ setAsideAt: "2026-11-26T12:00:00" })).toBe(true);
    expect(isSetAside({ setAsideAt: null })).toBe(false);
    expect(isSetAside({})).toBe(false);
  });

  it("names its reason", () => {
    expect(reasonLabel("online_only")).toBe("Online only");
    expect(reasonLabel(null)).toBe("Set aside");
  });
});

describe("already in the library", () => {
  it("matches the same name and year, not a remake", () => {
    const have = { title: "Resident Evil", year: "2002" };
    expect(sameTitle(have, { title: "resident evil", year: "2002" })).toBe(
      true,
    );
    expect(sameTitle(have, { title: "Resident Evil", year: "2026" })).toBe(
      false,
    );
    // no year on one side: the name decides
    expect(sameTitle(have, { title: "Resident Evil!", year: null })).toBe(true);
    expect(sameTitle(have, { title: "Resident Evil 2", year: null })).toBe(
      false,
    );
  });
});
