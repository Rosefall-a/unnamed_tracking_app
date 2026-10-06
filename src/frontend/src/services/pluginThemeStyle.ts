import {
  PALETTE_FIELDS,
  type CustomPalette,
  type PaletteId,
} from "./uiPalette";

interface ThemePalette {
  pluginId: string;
  contributionId: string;
  colors: CustomPalette;
}

// The palette is saved as an account-owned copy. Only active, approved theme
// contributions can identify that copy as a stylesheet scope.
export function pluginThemeStyleKey(
  palette: PaletteId,
  colors: CustomPalette,
  themes: readonly ThemePalette[],
): string | undefined {
  if (palette !== "custom") return undefined;
  const theme = themes.find((candidate) =>
    (["light", "dark"] as const).every((mode) =>
      PALETTE_FIELDS.every(
        ([role]) =>
          candidate.colors[mode]?.[role]?.toLowerCase() ===
          colors[mode]?.[role]?.toLowerCase(),
      ),
    ),
  );
  return theme ? `plugin:${theme.pluginId}:${theme.contributionId}` : undefined;
}

export function applyPluginThemeStyle(
  root: HTMLElement,
  palette: PaletteId,
  colors: CustomPalette,
  themes: readonly ThemePalette[],
  installedTheme = false,
): void {
  const key = installedTheme
    ? undefined
    : pluginThemeStyleKey(palette, colors, themes);
  if (key) root.dataset.pluginTheme = key;
  else delete root.dataset.pluginTheme;
}
