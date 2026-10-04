import { watch } from "vue";
import {
  preferences,
  preferencesLoaded,
  preferencesError,
} from "./preferences";
import type { Preferences } from "../services/preferences";
import { applyPalette } from "../services/uiPalette";
import {
  createDeviceAppearance,
  DEVICE_APPEARANCE_KEY,
  parseDeviceAppearance,
  updateBrowserThemeColor,
} from "../services/deviceAppearance";

export type UiTheme = Preferences["ui_theme"];
export type UiAppearance = Pick<
  Preferences,
  | "ui_theme"
  | "ui_palette"
  | "ui_custom_palette"
  | "ui_density"
  | "ui_style"
  | "ui_reduce_motion"
  | "ui_high_contrast"
>;

export function resolveUiTheme(
  theme: UiTheme,
  systemDark: boolean,
): "light" | "dark" {
  return theme === "system" ? (systemDark ? "dark" : "light") : theme;
}

// Sign-in, redirects and the neutral offline page share a cosmetic device cache.
// The authenticated account's server preferences remain authoritative.
export function initializeUiAppearance(): void {
  const system = window.matchMedia("(prefers-color-scheme: dark)");
  const root = document.documentElement;
  let initial: UiTheme = "system";
  let device = createDeviceAppearance(initial, "orange", {}, false);
  try {
    const cached = localStorage.getItem("ui-theme");
    if (cached === "light" || cached === "dark") initial = cached;
    device =
      parseDeviceAppearance(localStorage.getItem(DEVICE_APPEARANCE_KEY)) ??
      createDeviceAppearance(initial, "orange", {}, false);
  } catch {
    // Privacy modes can deny storage; appearance remains usable.
  }
  root.dataset.uiStyle = "archive-pocket";
  const apply = () => {
    const value = preferences.value;
    if (preferencesLoaded.value && !preferencesError.value) {
      device = createDeviceAppearance(
        value.ui_theme,
        value.ui_palette,
        value.ui_custom_palette,
        value.ui_high_contrast,
      );
      try {
        localStorage.setItem("ui-theme", value.ui_theme);
        localStorage.setItem(DEVICE_APPEARANCE_KEY, JSON.stringify(device));
      } catch {
        /* Server preferences still work without browser storage. */
      }
    }
    root.dataset.theme = resolveUiTheme(device.theme, system.matches);
    applyPalette(
      root,
      device.palette,
      resolveUiTheme(device.theme, system.matches),
      device.colors,
      device.highContrast,
    );
    root.dataset.uiStyle = value.ui_style;
    root.dataset.density = value.ui_density;
    root.classList.toggle("reduce-motion", value.ui_reduce_motion);
    root.classList.toggle("high-contrast", device.highContrast);
    root.classList.toggle("compact", value.ui_density === "compact");
    updateBrowserThemeColor(root);
  };
  apply();
  watch([preferences, preferencesLoaded], apply, { deep: true });
  system.addEventListener("change", apply);
}
