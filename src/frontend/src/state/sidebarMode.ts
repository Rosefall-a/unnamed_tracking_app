// A device-specific override; Auto chooses a full desktop pane, tablet rail,
// and phone bottom navigation. Explicit old choices remain available.
import { computed, ref, watch } from "vue";

export type SidebarMode = "auto" | "overlay" | "pinned" | "rail";

const STORAGE_KEY = "sidebarMode";

function readStored(): SidebarMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "pinned" || stored === "rail" || stored === "overlay"
      ? stored
      : "auto";
  } catch {
    return "auto";
  }
}

export const sidebarMode = ref<SidebarMode>(readStored());
export const navigationMenuOpen = ref(false);

watch(sidebarMode, (mode) => {
  try {
    localStorage.setItem(STORAGE_KEY, mode);
  } catch {
    /* Storage may be unavailable. */
  }
});

export const navigationViewport = ref<"phone" | "tablet" | "desktop">(
  "desktop",
);
export const effectiveSidebarMode = computed(() => {
  if (navigationViewport.value === "phone") return "overlay";
  if (sidebarMode.value !== "auto") return sidebarMode.value;
  return navigationViewport.value === "tablet" ? "rail" : "pinned";
});
export function initializeNavigationViewport(): () => void {
  const phone = window.matchMedia("(max-width: 760px)");
  const tablet = window.matchMedia("(max-width: 1100px)");
  const update = () => {
    navigationViewport.value = phone.matches
      ? "phone"
      : tablet.matches
        ? "tablet"
        : "desktop";
  };
  update();
  phone.addEventListener("change", update);
  tablet.addEventListener("change", update);
  return () => {
    phone.removeEventListener("change", update);
    tablet.removeEventListener("change", update);
  };
}

// Drag-resizable width for overlay and pinned modes (and rail's own
// hover-expanded width). The icon rail's collapsed width is fixed at 56px
// on purpose — that's the "just icons" point of the mode.
export const SIDEBAR_MIN_WIDTH = 200;
export const SIDEBAR_MAX_WIDTH = 440;
const WIDTH_STORAGE_KEY = "sidebarWidth";
const DEFAULT_WIDTH = 232;

function clampWidth(width: number): number {
  return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, width));
}

function readStoredWidth(): number {
  try {
    const stored = Number(localStorage.getItem(WIDTH_STORAGE_KEY));
    return Number.isFinite(stored) && stored > 0
      ? clampWidth(stored)
      : DEFAULT_WIDTH;
  } catch {
    return DEFAULT_WIDTH;
  }
}

export const sidebarWidth = ref<number>(readStoredWidth());

watch(sidebarWidth, (width) => {
  try {
    localStorage.setItem(WIDTH_STORAGE_KEY, String(width));
  } catch {
    /* Storage may be unavailable. */
  }
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
