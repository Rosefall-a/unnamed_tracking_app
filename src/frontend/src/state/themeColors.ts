// The colours someone has changed from the app's own. The app's colours are all
// tokens on the page (--ui-*), so changing one is setting that token; the shades
// built from it (a brighter accent, a lighter panel) are worked out here.
import { preferences } from "./preferences";

export const THEME_COLOR_KEYS = [
  "accent",
  "text",
  "dim",
  "heading",
  "background",
  "panels",
] as const;
export type ThemeColorKey = (typeof THEME_COLOR_KEYS)[number];
export type ThemeColors = Partial<Record<ThemeColorKey, string>>;

const CACHE_KEY = "themeColors";

// what each colour is, and what the app uses when it is not changed
export const THEME_COLOR_INFO: Record<
  ThemeColorKey,
  { label: string; hint: string; fallback: string }
> = {
  accent: {
    label: "Accent",
    hint: "Buttons, highlights and selected items",
    fallback: "#d68a34",
  },
  text: {
    label: "Text",
    hint: "Body text and titles on cards",
    fallback: "#f2f2f2",
  },
  dim: {
    label: "Secondary text",
    hint: "Descriptions, labels and hints",
    fallback: "#9c9c9c",
  },
  heading: {
    label: "Headings",
    hint: "Page and section headings",
    fallback: "#ffffff",
  },
  background: {
    label: "Background",
    hint: "The page behind everything",
    fallback: "#0d0d0d",
  },
  panels: {
    label: "Panels",
    hint: "Cards, dialogs and menus",
    fallback: "#1a1a1a",
  },
};

export const ACCENT_PRESETS = [
  "#d68a34",
  "#e5533d",
  "#d9568f",
  "#9b6df0",
  "#4f8cf0",
  "#2fb5a6",
  "#6fbf73",
  "#d6b834",
];

// dark text on a light colour and the other way round
function readableOn(hex: string): string {
  const n = parseInt(hex.slice(1), 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 150 ? "#14100a" : "#ffffff";
}

const mix = (a: string, pct: number, b: string) =>
  `color-mix(in srgb, ${a} ${pct}%, ${b})`;

function tokensFor(colors: ThemeColors): Record<string, string> {
  const out: Record<string, string> = {};
  const { accent, text, dim, heading, background, panels } = colors;
  if (accent) {
    out["--ui-accent"] = accent;
    out["--ui-accent-bright"] = mix(accent, 78, "#ffffff");
    out["--ui-on-accent"] = readableOn(accent);
    out["--ui-kind-game"] = accent;
  }
  if (text) {
    out["--ui-text"] = text;
    out["--ui-text-strong"] = mix(text, 92, "#000000");
    out["--ui-text-soft"] = mix(text, 84, "#000000");
    out["--ui-on-art"] = text;
  }
  if (dim) {
    out["--ui-dim"] = dim;
    out["--ui-dim-2"] = mix(dim, 92, "#000000");
    out["--ui-dim-3"] = dim;
    out["--ui-faint"] = mix(dim, 62, "#000000");
    out["--ui-faint-2"] = mix(dim, 75, "#000000");
  }
  if (heading) out["--ui-heading"] = heading;
  if (background) {
    out["--ui-bg"] = background;
    out["--ui-bg-2"] = mix("#ffffff", 4, background);
  }
  if (panels) {
    out["--ui-surface"] = panels;
    out["--ui-surface-2"] = mix("#ffffff", 5, panels);
    out["--ui-surface-3"] = mix("#ffffff", 9, panels);
    out["--ui-popover"] = mix("#000000", 12, panels);
  }
  return out;
}

const ALL_TOKENS = [
  "--ui-accent",
  "--ui-accent-bright",
  "--ui-on-accent",
  "--ui-kind-game",
  "--ui-text",
  "--ui-text-strong",
  "--ui-text-soft",
  "--ui-on-art",
  "--ui-dim",
  "--ui-dim-2",
  "--ui-dim-3",
  "--ui-faint",
  "--ui-faint-2",
  "--ui-heading",
  "--ui-bg",
  "--ui-bg-2",
  "--ui-surface",
  "--ui-surface-2",
  "--ui-surface-3",
  "--ui-popover",
];

export function applyThemeColors(colors: ThemeColors) {
  const root = document.documentElement.style;
  for (const name of ALL_TOKENS) root.removeProperty(name);
  for (const [name, value] of Object.entries(tokensFor(colors)))
    root.setProperty(name, value);
}

export function readCachedThemeColors(): ThemeColors {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as ThemeColors) : {};
  } catch {
    return {};
  }
}
export function cacheThemeColors(colors: ThemeColors) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(colors));
  } catch {
    // the copy only saves a flash on the next visit
  }
}

// the saved colours, once preferences are in; until then the cached ones stay
export function applySavedThemeColors() {
  const saved = preferences.value.theme_colors;
  if (saved && typeof saved === "object") {
    applyThemeColors(saved);
    cacheThemeColors(saved);
  }
}
