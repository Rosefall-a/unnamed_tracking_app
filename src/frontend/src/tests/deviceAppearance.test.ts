import { describe, expect, it } from "vitest";
import {
  createDeviceAppearance,
  parseDeviceAppearance,
} from "../services/deviceAppearance";
import { oidcButtonStyle } from "../services/oidc";
import { contrastRatio } from "../services/uiPalette";

describe("sign-in and offline device colors", () => {
  it("round-trips only cosmetic fields and discards unrelated account data", () => {
    const saved = createDeviceAppearance("system", "green", {}, true);
    expect(
      parseDeviceAppearance(
        JSON.stringify({
          ...saved,
          account_id: "discard",
          password: "discard",
        }),
      ),
    ).toEqual(saved);
    expect(saved.colors.light.accent).not.toBe(saved.colors.dark.accent);
  });
  it("rejects malformed, partial, oversized and CSS-valued device caches", () => {
    const saved = createDeviceAppearance("dark", "orange", {}, false);
    for (const raw of [
      null,
      "bad json",
      " ".repeat(4097),
      JSON.stringify({ ...saved, version: 2 }),
      JSON.stringify({ ...saved, theme: "unknown" }),
      JSON.stringify({ ...saved, colors: { light: saved.colors.light } }),
      JSON.stringify({
        ...saved,
        colors: {
          ...saved.colors,
          dark: {
            ...saved.colors.dark,
            background: "url(https://invalid.test)",
          },
        },
      }),
    ])
      expect(parseDeviceAppearance(raw)).toBeNull();
  });
  it("uses the palette for unbranded SSO and readable text for provider branding", () => {
    expect(oidcButtonStyle(null).backgroundColor).toBe("var(--ui-accent)");
    expect(oidcButtonStyle("invalid").color).toBe("var(--ui-on-accent)");
    for (const color of [
      "#d68a34",
      "#7557e8",
      "#ffffff",
      "#000000",
      "#777777",
      "#276641",
    ])
      expect(
        contrastRatio(color, oidcButtonStyle(color).color),
      ).toBeGreaterThanOrEqual(4.5);
  });
});
