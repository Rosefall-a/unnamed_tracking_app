import { describe, expect, it } from "vitest";
import { ORANGE_PALETTE } from "../services/uiPalette";
import {
  applyPluginThemeStyle,
  pluginThemeStyleKey,
} from "../services/pluginThemeStyle";

const theme = {
  pluginId: "example.theme-palettes",
  contributionId: "purple-blocks",
  colors: ORANGE_PALETTE,
};

describe("selected plugin stylesheet scope", () => {
  it("matches the saved copy in both modes, including uppercase colour values", () => {
    const custom = structuredClone(ORANGE_PALETTE);
    custom.dark.accent = custom.dark.accent.toUpperCase();
    expect(pluginThemeStyleKey("custom", custom, [theme])).toBe(
      "plugin:example.theme-palettes:purple-blocks",
    );
    custom.light.accent = "#aa00ff";
    expect(pluginThemeStyleKey("custom", custom, [theme])).toBeUndefined();
  });

  it("removes stylesheet scope when switching palettes or disabling the plugin", () => {
    const root = { dataset: {} } as HTMLElement;
    applyPluginThemeStyle(root, "custom", ORANGE_PALETTE, [theme]);
    expect(root.dataset.pluginTheme).toContain("purple-blocks");
    applyPluginThemeStyle(root, "green", ORANGE_PALETTE, [theme]);
    expect(root.dataset.pluginTheme).toBeUndefined();
    applyPluginThemeStyle(root, "custom", ORANGE_PALETTE, [theme]);
    applyPluginThemeStyle(root, "custom", ORANGE_PALETTE, []);
    expect(root.dataset.pluginTheme).toBeUndefined();
  });
});
