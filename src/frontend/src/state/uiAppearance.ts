import { watch } from "vue";
import { preferences } from "./preferences";
import type { Preferences } from "../services/preferences";

export type UiTheme = Preferences["ui_theme"];
export type UiAppearance = Pick<
  Preferences,
  | "ui_theme"
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

// Only the color preference is cached on the device to prevent an initial
// theme flash. The authenticated account's server preferences are authoritative.
export function initializeUiAppearance(): void {
  const system = window.matchMedia("(prefers-color-scheme: dark)");
  const root = document.documentElement;
  let initial: UiTheme = "system";
  try {
    const cached = localStorage.getItem("ui-theme");
    if (cached === "light" || cached === "dark") initial = cached;
  } catch {
    // Privacy modes can deny storage; appearance remains usable.
  }
  root.dataset.theme = resolveUiTheme(initial, system.matches);
  root.dataset.uiStyle = "archive-pocket";
  const apply = () => {
    const value = preferences.value;
    root.dataset.theme = resolveUiTheme(value.ui_theme, system.matches);
    root.dataset.uiStyle = value.ui_style;
    root.dataset.density = value.ui_density;
    root.classList.toggle("reduce-motion", value.ui_reduce_motion);
    root.classList.toggle("high-contrast", value.ui_high_contrast);
    root.classList.toggle("compact", value.ui_density === "compact");
    try {
      localStorage.setItem("ui-theme", value.ui_theme);
    } catch {
      // Server preferences still save when browser storage is unavailable.
    }
  };
  watch(preferences, apply, { deep: true });
  system.addEventListener("change", apply);
}
