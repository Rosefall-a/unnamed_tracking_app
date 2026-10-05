import { afterEach, describe, expect, it, vi } from "vitest";
import { createDeviceAppearance } from "../services/deviceAppearance";
import { DEFAULT_PREFERENCES } from "../services/preferences";
import {
  UI_PREFERENCES_COOKIE,
  readUiPreferencesCookie,
  saveUiPreferencesCookie,
} from "../services/uiPreferencesCookie";

afterEach(() => vi.unstubAllGlobals());
describe("cosmetic preference cookies", () => {
  it("round-trips appearance and layout with safe flags and without account data", () => {
    const document = { cookie: "" };
    vi.stubGlobal("document", document);
    vi.stubGlobal("location", { protocol: "https:" });
    const value = {
      ...DEFAULT_PREFERENCES,
      ui_theme: "dark" as const,
      ui_palette: "green" as const,
      ui_density: "compact" as const,
      ui_reduce_motion: true,
      ui_welcome_completed: true,
      home_widgets: ["private-collection"],
      account_id: "private-account",
    };
    const device = createDeviceAppearance(
      value.ui_theme,
      value.ui_palette,
      {},
      false,
    );
    saveUiPreferencesCookie(device, value);
    expect(document.cookie).toContain(
      "; Path=/; Max-Age=31536000; SameSite=Lax; Secure",
    );
    expect(document.cookie.length).toBeLessThan(4000);
    expect(document.cookie).not.toMatch(
      /private|welcome|home_widgets|account_id/,
    );
    expect(readUiPreferencesCookie()).toEqual({
      ...device,
      density: "compact",
      style: "archive-pocket",
      reduceMotion: true,
      scope: "account",
      themePackage: "server",
    });
    vi.stubGlobal("location", { protocol: "http:" });
    saveUiPreferencesCookie(device, value);
    expect(document.cookie).not.toContain("; Secure");
  });
  it("ignores malformed, oversized, partial and CSS-valued cookies", () => {
    const device = createDeviceAppearance("light", "orange", {}, false);
    const valid = {
      ...device,
      density: "comfortable",
      style: "archive-pocket",
      reduceMotion: false,
    };
    for (const raw of [
      "%",
      encodeURIComponent("null"),
      "x".repeat(4097),
      encodeURIComponent(JSON.stringify({ ...valid, density: "tiny" })),
      encodeURIComponent(JSON.stringify({ ...valid, reduceMotion: "yes" })),
      encodeURIComponent(JSON.stringify({ ...valid, scope: "everywhere" })),
      encodeURIComponent(
        JSON.stringify({ ...valid, themePackage: "../bad.css" }),
      ),
      encodeURIComponent(
        JSON.stringify({ ...valid, colors: { light: device.colors.light } }),
      ),
      encodeURIComponent(
        JSON.stringify({
          ...valid,
          colors: {
            ...device.colors,
            dark: { ...device.colors.dark, text: "url(https://invalid.test)" },
          },
        }),
      ),
    ]) {
      vi.stubGlobal("document", { cookie: `${UI_PREFERENCES_COOKIE}=${raw}` });
      expect(readUiPreferencesCookie()).toBeNull();
    }
  });
  it("discards unrelated values and tolerates blocked cookie access", () => {
    const device = createDeviceAppearance("system", "custom", {}, true);
    vi.stubGlobal("document", {
      cookie: `unrelated=1; ${UI_PREFERENCES_COOKIE}=${encodeURIComponent(JSON.stringify({ ...device, density: "compact", style: "archive-pocket", reduceMotion: true, password: "discard" }))}`,
    });
    expect(readUiPreferencesCookie()).not.toHaveProperty("password");
    vi.stubGlobal("document", {
      get cookie() {
        throw new Error("blocked");
      },
      set cookie(_value: string) {
        throw new Error("blocked");
      },
    });
    vi.stubGlobal("location", { protocol: "https:" });
    expect(readUiPreferencesCookie()).toBeNull();
    expect(() =>
      saveUiPreferencesCookie(device, DEFAULT_PREFERENCES),
    ).not.toThrow();
  });
  it("keeps device scope and the selected package in the cosmetic cookie", () => {
    vi.stubGlobal("document", { cookie: "" });
    vi.stubGlobal("location", { protocol: "https:" });
    const value = {
      ...DEFAULT_PREFERENCES,
      ui_theme_package: "official.forest",
    };
    saveUiPreferencesCookie(
      createDeviceAppearance("dark", "green", {}, false),
      value,
      "device",
    );
    expect(readUiPreferencesCookie()).toMatchObject({
      scope: "device",
      themePackage: "official.forest",
      theme: "dark",
      palette: "green",
    });
  });
});
