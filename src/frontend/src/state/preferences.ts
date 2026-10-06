// The signed-in user's server-side preferences, loaded once and shared, so
// pages that depend on one (a default layout, a default sort) can read it
// without each fetching it. Settings updates it as it saves.
import { ref } from "vue";
import {
  DEFAULT_PREFERENCES,
  fetchPreferences,
  invalidateQueuedPreferences,
} from "../services/preferences";
import type { Preferences } from "../services/preferences";

export const preferences = ref<Preferences>({ ...DEFAULT_PREFERENCES });
export const preferencesLoaded = ref(false);
export const preferencesError = ref<string | null>(null);
let generation = 0;

export function resetSharedPreferences(): void {
  generation++;
  invalidateQueuedPreferences();
  preferences.value = { ...DEFAULT_PREFERENCES };
  preferencesLoaded.value = false;
  preferencesError.value = null;
}

export async function loadSharedPreferences(): Promise<void> {
  const request = ++generation;
  preferencesError.value = null;
  try {
    const loaded = await fetchPreferences();
    if (request === generation) preferences.value = loaded;
  } catch (error) {
    if (request === generation)
      preferencesError.value =
        error instanceof Error ? error.message : "Could not load preferences.";
  } finally {
    if (request === generation) preferencesLoaded.value = true;
  }
}
