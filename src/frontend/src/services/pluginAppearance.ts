import { ORANGE_PALETTE, paletteTokens, type PaletteMode } from "./uiPalette";

// Only cosmetic public tokens cross the opaque iframe boundary.
export const PLUGIN_APPEARANCE_TOKENS = [
  ...Object.keys(paletteTokens("orange", "light")),
  "--ui-font-family",
  "--ui-font-small",
  "--ui-font-heading",
  "--ui-control-height",
  "--ui-radius-control",
  "--ui-radius-card",
  "--ui-radius-row",
  "--ui-focus-ring",
] as const;
export interface PluginAppearance {
  api_contract_version: "1.1.0";
  mode: PaletteMode;
  high_contrast: boolean;
  reduce_motion: boolean;
  tokens: Record<string, string>;
}
export function readPluginAppearance(): PluginAppearance {
  const root =
    typeof document === "undefined" ? null : document.documentElement;
  const style = root ? getComputedStyle(root) : null;
  return {
    api_contract_version: "1.1.0",
    mode: root?.dataset.theme === "dark" ? "dark" : "light",
    high_contrast: root?.classList.contains("high-contrast") ?? false,
    reduce_motion: root?.classList.contains("reduce-motion") ?? false,
    tokens: Object.fromEntries(
      PLUGIN_APPEARANCE_TOKENS.map((token) => [
        token,
        style?.getPropertyValue(token).trim() ||
          paletteTokens("orange", "light", ORANGE_PALETTE)[token] ||
          "",
      ]),
    ),
  };
}
export function observePluginAppearance(
  callback: (appearance: PluginAppearance) => void,
): () => void {
  callback(readPluginAppearance());
  if (typeof document === "undefined") return () => {};
  const observer = new MutationObserver(() => callback(readPluginAppearance()));
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: [
      "style",
      "class",
      "data-theme",
      "data-density",
      "data-palette",
    ],
  });
  return () => observer.disconnect();
}
