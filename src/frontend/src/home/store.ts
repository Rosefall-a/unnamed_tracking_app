// The Home layout you are looking at. The server keeps it per account; a copy in
// the browser lets the page draw in the right place on first paint instead of
// flashing the default while preferences load.
import { ref, watch } from "vue";
import { queuePreferences } from "../services/preferences";
import { preferences, preferencesLoaded } from "../state/preferences";
import { cloneLayout, defaultLayout, normaliseLayout } from "./layout";
import type { HomeLayout } from "./layout";

const CACHE_KEY = "homeLayout";

function readCache(): HomeLayout | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? normaliseLayout(JSON.parse(raw)) : null;
  } catch {
    return null;
  }
}
function writeCache(layout: HomeLayout) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(layout));
  } catch {
    // the copy only saves a flash on the next visit
  }
}

export const savedLayout = ref<HomeLayout>(readCache() ?? defaultLayout());

watch(
  preferencesLoaded,
  (ready) => {
    if (!ready) return;
    if (preferences.value.home_layout) {
      savedLayout.value = normaliseLayout(preferences.value.home_layout);
      writeCache(savedLayout.value);
    }
  },
  { immediate: true },
);

export const saveError = ref<string | null>(null);

export async function saveLayout(layout: HomeLayout): Promise<boolean> {
  const clean = normaliseLayout(layout);
  savedLayout.value = clean;
  writeCache(clean);
  saveError.value = null;
  try {
    await queuePreferences({ home_layout: clean });
    preferences.value = { ...preferences.value, home_layout: clean };
    return true;
  } catch (e) {
    saveError.value =
      e instanceof Error ? e.message : "Could not save your layout.";
    return false;
  }
}

export function startDraft(): HomeLayout {
  return cloneLayout(savedLayout.value);
}

// A change made from controls on a widget while the page is not being edited.
// It shows at once and is saved a moment later, so several quick changes in a
// row make one save.
let pending: number | undefined;
export function updateWidgetSettings(
  id: string,
  settings: Record<string, unknown>,
  variant: string | null,
) {
  const next = cloneLayout(savedLayout.value);
  for (const page of next.pages) {
    const w = page.widgets.find((item) => item.id === id);
    if (w) {
      w.settings = settings;
      w.variant = variant;
    }
  }
  savedLayout.value = next;
  writeCache(next);
  window.clearTimeout(pending);
  pending = window.setTimeout(() => {
    pending = undefined;
    void saveLayout(savedLayout.value);
  }, 600);
}

// Saves a change that is still waiting its turn, for when the page is being left.
export function flushPending() {
  if (pending === undefined) return;
  window.clearTimeout(pending);
  pending = undefined;
  void saveLayout(savedLayout.value);
}
