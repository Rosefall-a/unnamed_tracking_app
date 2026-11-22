// How the sidebar behaves: overlay (default, hidden until the menu button
// opens it), pinned (always visible at full width, in flow), or rail
// (always visible collapsed to icons, expands on hover). Saved on the server
// with the person's other page choices (state/uiState.ts).
import { computed, ref } from "vue";
import { getUi, setUi } from "./uiState";

export type SidebarMode = "overlay" | "pinned" | "rail";

const STORAGE_KEY = "sidebarMode";

export const sidebarMode = computed<SidebarMode>({
  get: () => {
    const stored = getUi<unknown>(STORAGE_KEY, null);
    return stored === "pinned" || stored === "rail" ? stored : "overlay";
  },
  set: (mode) => setUi(STORAGE_KEY, mode),
});

// Drag-resizable width for overlay and pinned modes (and rail's own
// hover-expanded width). The icon rail's collapsed width is fixed at 56px
// on purpose — that's the "just icons" point of the mode.
export const SIDEBAR_MIN_WIDTH = 200;
export const SIDEBAR_MAX_WIDTH = 440;
const WIDTH_STORAGE_KEY = "sidebarWidth";
const DEFAULT_WIDTH = 270;

function clampWidth(width: number): number {
  return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, width));
}

export const sidebarWidth = computed<number>({
  get: () => {
    const stored = Number(getUi<unknown>(WIDTH_STORAGE_KEY, 0));
    return stored ? clampWidth(stored) : DEFAULT_WIDTH;
  },
  set: (width) => setUi(WIDTH_STORAGE_KEY, width),
});

export function setSidebarWidth(width: number) {
  sidebarWidth.value = clampWidth(width);
}

export function resetSidebarWidth() {
  sidebarWidth.value = DEFAULT_WIDTH;
}

// True for the duration of a resize drag, so App.vue can turn off its
// content margin transition too — otherwise the page trails behind the
// pointer instead of tracking it while dragging.
export const sidebarResizing = ref(false);
