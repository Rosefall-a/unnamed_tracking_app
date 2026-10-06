import {
  PALETTE_FIELDS,
  type PaletteColors,
  type PaletteMode,
} from "./uiPalette";

export const PALETTE_FILE_LIMIT = 8192;
export type SharedPalette = Record<PaletteMode, PaletteColors>;

export function readPaletteFile(text: string): SharedPalette {
  if (new TextEncoder().encode(text).length > PALETTE_FILE_LIMIT)
    throw new Error("Palette files must be smaller than 8 KB.");
  let file;
  try {
    file = JSON.parse(text);
  } catch {
    throw new Error("Choose a valid palette JSON file.");
  }
  if (file?.format !== "uta-color-palette" || file.version !== 1)
    throw new Error("This palette file format or version is not supported.");
  const result = {} as SharedPalette;
  for (const mode of ["light", "dark"] as const) {
    const colors = file.colors?.[mode];
    if (
      !colors ||
      typeof colors !== "object" ||
      Array.isArray(colors) ||
      Object.keys(colors).length !== PALETTE_FIELDS.length
    )
      throw new Error(
        `The ${mode} palette must include all ${PALETTE_FIELDS.length} colors.`,
      );
    result[mode] = {} as PaletteColors;
    for (const [role] of PALETTE_FIELDS) {
      const value = colors[role];
      if (typeof value !== "string" || !/^#[0-9a-f]{6}$/i.test(value))
        throw new Error(`The ${mode} ${role} color must use #RRGGBB.`);
      result[mode][role] = value.toLowerCase();
    }
  }
  return result;
}

export function writePaletteFile(colors: SharedPalette): string {
  return (
    JSON.stringify(
      { format: "uta-color-palette", version: 1, colors },
      null,
      2,
    ) + "\n"
  );
}
