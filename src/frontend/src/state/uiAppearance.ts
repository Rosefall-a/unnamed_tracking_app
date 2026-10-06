import { computed, ref, watch } from "vue";
import {
  preferences,
  preferencesLoaded,
  preferencesError,
} from "./preferences";
import type { Preferences } from "../services/preferences";
import { applyPalette } from "../services/uiPalette";
import { resolveInstalledTheme, themeStylesheetUrl } from "../services/themes";
import { refreshThemes, themeCatalogue } from "./themes";
import {
  readUiPreferencesCookie,
  saveUiPreferencesCookie,
} from "../services/uiPreferencesCookie";
import {
  createDeviceAppearance,
  DEVICE_APPEARANCE_KEY,
  parseDeviceAppearance,
  updateBrowserThemeColor,
} from "../services/deviceAppearance";

export type UiTheme = Preferences["ui_theme"];
export const resolvedUiTheme = ref<"light" | "dark">("light");
export type UiAppearance = Pick<
  Preferences,
  | "ui_theme"
  | "ui_theme_package"
  | "ui_palette"
  | "ui_custom_palette"
  | "ui_density"
  | "ui_style"
  | "ui_reduce_motion"
  | "ui_high_contrast"
>;
const cosmeticKeys = [
  "ui_theme",
  "ui_theme_package",
  "ui_palette",
  "ui_custom_palette",
  "ui_high_contrast",
] as const;
type CosmeticAppearance = Pick<UiAppearance, (typeof cosmeticKeys)[number]>;
const cachedAppearance = readUiPreferencesCookie();
export const appearanceScope = ref<"account" | "device">(
  cachedAppearance?.scope ?? "account",
);
const devicePreferences = ref<CosmeticAppearance>({
  ui_theme: cachedAppearance?.theme ?? "system",
  ui_theme_package: cachedAppearance?.themePackage ?? "server",
  ui_palette: cachedAppearance?.palette ?? "orange",
  ui_custom_palette: cachedAppearance?.colors ?? {},
  ui_high_contrast: cachedAppearance?.highContrast ?? false,
});
export const appearancePreferences = computed<UiAppearance>(() => ({
  ...preferences.value,
  ...(appearanceScope.value === "device" ? devicePreferences.value : {}),
}));
export const activeInstalledTheme = computed(() =>
  resolveInstalledTheme(
    themeCatalogue.value,
    appearancePreferences.value.ui_theme_package,
    resolvedUiTheme.value,
  ),
);
export function changeAppearanceScope(scope: "account" | "device"): void {
  if (scope === appearanceScope.value) return;
  if (scope === "device") {
    const current = appearancePreferences.value;
    devicePreferences.value = Object.fromEntries(
      cosmeticKeys.map((key) => [key, current[key]]),
    ) as CosmeticAppearance;
  }
  appearanceScope.value = scope;
}
export function changeDeviceAppearance(changes: Partial<Preferences>): boolean {
  if (
    appearanceScope.value !== "device" ||
    !Object.keys(changes).every((key) =>
      cosmeticKeys.includes(key as (typeof cosmeticKeys)[number]),
    )
  )
    return false;
  devicePreferences.value = { ...devicePreferences.value, ...changes };
  return true;
}

export function resolveUiTheme(
  theme: UiTheme,
  systemDark: boolean,
): "light" | "dark" {
  return theme === "system" ? (systemDark ? "dark" : "light") : theme;
}

// Sign-in, redirects and the neutral offline page share a cosmetic device cache.
// Account choices remain authoritative unless this browser explicitly opts into device appearance.
export function initializeUiAppearance(): void {
  const system = window.matchMedia("(prefers-color-scheme: dark)");
  const root = document.documentElement;
  let initial: UiTheme = "system";
  let device = createDeviceAppearance(initial, "orange", {}, false);
  const cookie = readUiPreferencesCookie();
  let density: UiAppearance["ui_density"] = cookie?.density ?? "comfortable";
  let style: UiAppearance["ui_style"] = cookie?.style ?? "archive-pocket";
  let reduceMotion = cookie?.reduceMotion ?? false;
  let themePackage = cookie?.themePackage ?? "server";
  try {
    const cached = localStorage.getItem("ui-theme");
    if (cached === "light" || cached === "dark") initial = cached;
    device =
      cookie ??
      parseDeviceAppearance(localStorage.getItem(DEVICE_APPEARANCE_KEY)) ??
      createDeviceAppearance(initial, "orange", {}, false);
  } catch {
    // Privacy modes can deny storage; appearance remains usable.
  }
  if (cookie) device = cookie;
  root.dataset.uiStyle = "archive-pocket";
  const apply = () => {
    const value = appearancePreferences.value;
    if (preferencesLoaded.value && !preferencesError.value) {
      device = createDeviceAppearance(
        value.ui_theme,
        value.ui_palette,
        value.ui_custom_palette,
        value.ui_high_contrast,
      );
      density = value.ui_density;
      style = value.ui_style;
      reduceMotion = value.ui_reduce_motion;
      themePackage = value.ui_theme_package;
      saveUiPreferencesCookie(device, value, appearanceScope.value);
      try {
        localStorage.setItem("ui-theme", value.ui_theme);
        localStorage.setItem(DEVICE_APPEARANCE_KEY, JSON.stringify(device));
      } catch {
        /* Server preferences still work without browser storage. */
      }
    }
    root.dataset.theme = resolveUiTheme(device.theme, system.matches);
    resolvedUiTheme.value = resolveUiTheme(device.theme, system.matches);
    const installed = resolveInstalledTheme(
      themeCatalogue.value,
      themePackage,
      resolvedUiTheme.value,
    );
    applyPalette(
      root,
      installed ? "orange" : device.palette,
      resolveUiTheme(device.theme, system.matches),
      device.colors,
      device.highContrast,
    );
    root.dataset.uiStyle = style;
    root.dataset.density = density;
    root.classList.toggle("reduce-motion", reduceMotion);
    root.classList.toggle("high-contrast", device.highContrast);
    root.classList.toggle("compact", density === "compact");
    root.dataset.themePackage = installed?.id ?? "native";
    if (!installed) root.dataset.themeRevision = "native";
    try {
      localStorage.setItem("ui-theme-package", installed?.id ?? "native");
      localStorage.setItem(
        "ui-theme-stylesheet",
        installed ? themeStylesheetUrl(installed) : "",
      );
    } catch {
      /* Offline cosmetic styling is optional when storage is blocked. */
    }
    const currentStylesheet = document.getElementById(
      "uta-installed-theme",
    ) as HTMLLinkElement | null;
    const stylesheet = installed ? themeStylesheetUrl(installed) : null;
    if (currentStylesheet?.getAttribute("href") !== stylesheet) {
      currentStylesheet?.remove();
      if (stylesheet) {
        const link = document.createElement("link");
        link.id = "uta-installed-theme";
        link.rel = "stylesheet";
        link.href = stylesheet;
        link.addEventListener(
          "load",
          () => {
            if (!link.isConnected) return;
            root.dataset.themeRevision = installed?.digest ?? "native";
            updateBrowserThemeColor(root);
          },
          { once: true },
        );
        document.head.append(link);
      }
    }
    updateBrowserThemeColor(root);
  };
  apply();
  watch(
    [
      preferences,
      preferencesLoaded,
      preferencesError,
      devicePreferences,
      appearanceScope,
      themeCatalogue,
    ],
    apply,
    { deep: true },
  );
  system.addEventListener("change", apply);
  void refreshThemes();
}
