import { beforeEach, describe, expect, it } from "vitest";
import {
  resolveInstalledTheme,
  themeStylesheetUrl,
  type InstalledTheme,
  type ThemeCatalogue,
} from "../services/themes";
import {
  appearancePreferences,
  appearanceScope,
  changeAppearanceScope,
  changeDeviceAppearance,
} from "../state/uiAppearance";
import { preferences } from "../state/preferences";
import { DEFAULT_PREFERENCES } from "../services/preferences";

const theme: InstalledTheme = {
  format_version: 1,
  id: "official.forest",
  name: "Forest",
  version: "1.0.0",
  publisher: "Review publisher",
  description: "Green",
  kind: "official",
  stylesheet: "styles/main.css",
  supports: ["light", "dark"],
  digest: "a".repeat(64),
  enabled: true,
};
const catalogue: ThemeCatalogue = { default_theme: theme.id, themes: [theme] };
beforeEach(() => {
  appearanceScope.value = "account";
  preferences.value = { ...DEFAULT_PREFERENCES };
});
describe("installed theme choices", () => {
  it("follows the server default or an explicit native/personal selection", () => {
    expect(resolveInstalledTheme(catalogue, "server", "dark")).toBe(theme);
    expect(resolveInstalledTheme(catalogue, theme.id, "light")).toBe(theme);
    expect(resolveInstalledTheme(catalogue, "native", "dark")).toBeUndefined();
    expect(themeStylesheetUrl(theme)).toBe(
      `/api/themes/assets/official.forest/${theme.digest}/styles/main.css`,
    );
  });
  it("does not load disabled, deleted or mode-incompatible themes", () => {
    expect(
      resolveInstalledTheme(catalogue, "removed", "light"),
    ).toBeUndefined();
    expect(
      resolveInstalledTheme(
        { ...catalogue, themes: [{ ...theme, enabled: false }] },
        "server",
        "light",
      ),
    ).toBeUndefined();
    expect(
      resolveInstalledTheme(
        { ...catalogue, themes: [{ ...theme, supports: ["dark"] }] },
        theme.id,
        "light",
      ),
    ).toBeUndefined();
  });
  it("keeps device colors and package choices separate from account and layout settings", () => {
    preferences.value = {
      ...DEFAULT_PREFERENCES,
      ui_theme: "dark",
      ui_theme_package: theme.id,
      ui_density: "compact",
    };
    changeAppearanceScope("device");
    expect(appearancePreferences.value.ui_theme_package).toBe(theme.id);
    expect(
      changeDeviceAppearance({
        ui_theme: "light",
        ui_palette: "green",
        ui_theme_package: "native",
      }),
    ).toBe(true);
    expect(preferences.value.ui_theme).toBe("dark");
    expect(preferences.value.ui_theme_package).toBe(theme.id);
    expect(appearancePreferences.value).toMatchObject({
      ui_theme: "light",
      ui_palette: "green",
      ui_theme_package: "native",
      ui_density: "compact",
    });
    expect(changeDeviceAppearance({ ui_density: "comfortable" })).toBe(false);
    expect(changeDeviceAppearance({ home_widgets: ["private"] })).toBe(false);
    changeAppearanceScope("account");
    expect(appearancePreferences.value.ui_theme).toBe("dark");
    expect(appearancePreferences.value.ui_theme_package).toBe(theme.id);
    expect(changeDeviceAppearance({ ui_theme: "light" })).toBe(false);
  });
});
