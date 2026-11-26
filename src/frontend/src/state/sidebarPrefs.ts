// What the sidebar shows, on top of sidebarMode (when it shows). Style, counts,
// search and the Jump back in list are how this device shows things, so they
// stay in this browser like sidebarMode does. Pinned items are something the
// person made, so they are saved on the server with their other page choices
// (see SERVER_NAMES in uiState.ts).
import { computed } from "vue";
import { getUi, setUi } from "./uiState";

export type SidebarStyle =
  | "classic"
  | "minimal"
  | "library"
  | "railpanel"
  | "peek"
  | "topbar"
  | "guide"
  | "dock";
export const SIDEBAR_STYLES: SidebarStyle[] = [
  "classic",
  "library",
  "railpanel",
  "minimal",
  "peek",
  "topbar",
  "guide",
  "dock",
];
export type MediaOpensOn = "anime" | "movies" | "tv" | "last";

function pref<T>(key: string, fallback: T, valid: (v: unknown) => boolean) {
  return computed<T>({
    get: () => {
      const v = getUi<unknown>(key, fallback);
      return valid(v) ? (v as T) : fallback;
    },
    set: (v) => setUi(key, v),
  });
}

export const sidebarStyle = pref<SidebarStyle>("sidebarStyle", "classic", (v) =>
  SIDEBAR_STYLES.includes(v as SidebarStyle),
);
export const sidebarShowJump = pref<boolean>(
  "sidebarShowJump",
  true,
  (v) => typeof v === "boolean",
);
export const JUMP_COUNTS = [3, 4, 6] as const;
export const sidebarJumpCount = pref<number>("sidebarJumpCount", 4, (v) =>
  JUMP_COUNTS.includes(v as 3 | 4 | 6),
);
export const sidebarShowCounts = pref<boolean>(
  "sidebarShowCounts",
  true,
  (v) => typeof v === "boolean",
);
export const sidebarShowSearch = pref<boolean>(
  "sidebarShowSearch",
  true,
  (v) => typeof v === "boolean",
);
export const mediaOpensOn = pref<MediaOpensOn>(
  "mediaOpensOn",
  "last",
  (v) => v === "anime" || v === "movies" || v === "tv" || v === "last",
);
// the media page opened most recently, for "last"
export const lastMediaPage = pref<string>(
  "lastMediaPage",
  "/anime",
  (v) => v === "/anime" || v === "/movies" || v === "/tv",
);

export function mediaHome(): string {
  const pick = mediaOpensOn.value;
  if (pick === "anime") return "/anime";
  if (pick === "movies") return "/movies";
  if (pick === "tv") return "/tv";
  return lastMediaPage.value;
}

// A pinned title: what the sidebar needs to show and open it.
export interface SidebarPin {
  key: string;
  title: string;
  art: string | null;
  to: string;
  kind: string;
}

export const sidebarPins = computed<SidebarPin[]>({
  get: () => {
    const v = getUi<unknown>("sidebarPins", []);
    return Array.isArray(v)
      ? (v as SidebarPin[]).filter((p) => p && typeof p.key === "string")
      : [];
  },
  set: (v) => setUi("sidebarPins", v),
});

export function isPinned(key: string): boolean {
  return sidebarPins.value.some((p) => p.key === key);
}
export function togglePin(pin: SidebarPin): void {
  sidebarPins.value = isPinned(pin.key)
    ? sidebarPins.value.filter((p) => p.key !== pin.key)
    : [...sidebarPins.value, pin];
}
export function movePin(key: string, by: -1 | 1): void {
  const list = [...sidebarPins.value];
  const i = list.findIndex((p) => p.key === key);
  const j = i + by;
  if (i < 0 || j < 0 || j >= list.length) return;
  [list[i], list[j]] = [list[j], list[i]];
  sidebarPins.value = list;
}
