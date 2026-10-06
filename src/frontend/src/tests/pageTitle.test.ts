import { describe, expect, it } from "vitest";

import { formatDocumentTitle } from "../state/pageTitle";
import { branding } from "../state/branding";

describe("formatDocumentTitle (#85)", () => {
  it("names the page and the app instead of 'frontend'", () => {
    expect(formatDocumentTitle("Settings")).toBe("Settings | Archive");
    expect(formatDocumentTitle(null)).toBe("Archive");
  });

  it("prefixes unread notifications", () => {
    expect(formatDocumentTitle("Hades", 2)).toBe("(2) Hades | Archive");
    expect(formatDocumentTitle("Home", 150)).toBe("(99+) Home | Archive");
    expect(formatDocumentTitle("Home", 0)).toBe("Home | Archive");
  });

  it("uses the configured public app name without changing the page title", () => {
    const previous = branding.value;
    try {
      branding.value = { ...previous, app_name: "My library" };
      expect(formatDocumentTitle("Settings", 2)).toBe(
        "(2) Settings | My library",
      );
    } finally {
      branding.value = previous;
    }
  });
});
