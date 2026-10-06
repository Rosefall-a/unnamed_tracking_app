import {
  PALETTE_FIELDS,
  paletteColors,
  type PaletteColors,
  type PaletteId,
} from "./uiPalette";

// Cosmetic device preference only. Never include account identifiers or application data.
export const DEVICE_APPEARANCE_KEY = "ui-appearance";
export interface DeviceAppearance {
  version: 1;
  theme: "light" | "dark" | "system";
  palette: PaletteId;
  colors: Record<"light" | "dark", PaletteColors>;
  highContrast: boolean;
}

export function parseDeviceAppearance(
  raw: string | null,
): DeviceAppearance | null {
  if (!raw || raw.length > 4096) return null;
  try {
    const value = JSON.parse(raw);
    if (
      value.version !== 1 ||
      !["light", "dark", "system"].includes(value.theme) ||
      !["orange", "green", "custom"].includes(value.palette) ||
      typeof value.highContrast !== "boolean"
    )
      return null;
    for (const mode of ["light", "dark"] as const) {
      const colors = value.colors?.[mode];
      if (
        !colors ||
        Object.keys(colors).length !== PALETTE_FIELDS.length ||
        PALETTE_FIELDS.some(
          ([role]) =>
            typeof colors[role] !== "string" ||
            !/^#[0-9a-f]{6}$/i.test(colors[role]),
        )
      )
        return null;
    }
    // Reconstruct only the public color fields, discarding unrelated input.
    return {
      version: 1,
      theme: value.theme,
      palette: value.palette,
      highContrast: value.highContrast,
      colors: {
        light: Object.fromEntries(
          PALETTE_FIELDS.map(([role]) => [role, value.colors.light[role]]),
        ) as PaletteColors,
        dark: Object.fromEntries(
          PALETTE_FIELDS.map(([role]) => [role, value.colors.dark[role]]),
        ) as PaletteColors,
      },
    };
  } catch {
    return null;
  }
}

export function createDeviceAppearance(
  theme: DeviceAppearance["theme"],
  palette: PaletteId,
  custom: Partial<Record<"light" | "dark", PaletteColors>>,
  highContrast: boolean,
): DeviceAppearance {
  return {
    version: 1,
    theme,
    palette,
    colors: {
      light: paletteColors(palette, "light", custom),
      dark: paletteColors(palette, "dark", custom),
    },
    highContrast,
  };
}

export function updateBrowserThemeColor(root: HTMLElement): void {
  let meta = document.querySelector<HTMLMetaElement>(
    'meta[name="theme-color"]',
  );
  if (!meta) {
    meta = document.createElement("meta");
    meta.name = "theme-color";
    document.head.append(meta);
  }
  meta.content = getComputedStyle(root).getPropertyValue("--ui-bg").trim();
}
