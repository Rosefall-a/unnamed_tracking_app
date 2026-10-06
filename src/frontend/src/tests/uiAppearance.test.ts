import { describe, expect, it } from "vitest";
import { resolveUiTheme } from "../state/uiAppearance";

describe("appearance theme policy", () => {
  it("follows system changes only when System is selected", () => {
    expect(resolveUiTheme("system", true)).toBe("dark");
    expect(resolveUiTheme("system", false)).toBe("light");
    expect(resolveUiTheme("light", true)).toBe("light");
    expect(resolveUiTheme("dark", false)).toBe("dark");
  });
});
