const PLATFORM_FAMILY_MAP: Record<string, string> = {
    ps5: 'PlayStation',
    ps4: 'PlayStation',
    ps3: 'PlayStation',
    ps2: 'PlayStation',
    ps1: 'PlayStation',
    'playstation 5': 'PlayStation',
    'playstation 4': 'PlayStation',
    'playstation 3': 'PlayStation',
    playstation: 'PlayStation',
    psp: 'PlayStation',
    'ps vita': 'PlayStation',
    vita: 'PlayStation',
    'xbox series x': 'Xbox',
    'xbox series s': 'Xbox',
    'xbox one': 'Xbox',
    'xbox 360': 'Xbox',
    xbox: 'Xbox',
    switch: 'Nintendo',
    'nintendo switch': 'Nintendo',
    'wii u': 'Nintendo',
    wii: 'Nintendo',
    gamecube: 'Nintendo',
    '3ds': 'Nintendo',
    'nintendo 3ds': 'Nintendo',
    ds: 'Nintendo',
    'nintendo ds': 'Nintendo',
    nes: 'Nintendo',
    snes: 'Nintendo',
    n64: 'Nintendo',
    'game boy': 'Nintendo',
    gameboy: 'Nintendo',
    pc: 'PC',
    windows: 'PC',
    steam: 'PC',
    mac: 'PC',
    linux: 'PC',
}

export function normalizePlatformFamily(raw: string): string {
    const key = raw.trim().toLowerCase()
    return PLATFORM_FAMILY_MAP[key] ?? raw.trim()
}

// Shown in the platform filter by default — the systems most libraries
// actually revolve around. Kept short on purpose so the dropdown isn't a wall
// of consoles before anyone's typed anything.
export const PLATFORM_OPTIONS = ['PC', 'PlayStation', 'Xbox', 'Nintendo']

// Only surfaced once the user starts typing (see FilterCombobox's
// extraOptions) — retro/less-common systems are searchable without cluttering
// the default list. Anything typed that isn't here still works —
// normalizePlatformFamily just passes it through unchanged.
export const RETRO_PLATFORM_OPTIONS = [
    'Arcade',
    'Atari 2600',
    'Atari 5200',
    'Atari 7800',
    'Atari Jaguar',
    'Sega Genesis',
    'Sega Saturn',
    'Sega Dreamcast',
    'Sega Game Gear',
    'Sega Master System',
    'TurboGrafx-16',
    'Neo Geo',
    'Commodore 64',
    'Amiga',
    'ZX Spectrum',
    'MS-DOS',
    '3DO',
]
