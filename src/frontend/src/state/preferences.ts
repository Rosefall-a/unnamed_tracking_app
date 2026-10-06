// The signed-in user's server-side preferences, loaded once and shared, so
// pages that depend on one (a default layout, a default sort) can read it
// without each fetching it. Settings updates it as it saves.
import { ref } from "vue";
import { DEFAULT_PREFERENCES, fetchPreferences } from "../services/preferences";
import type { Preferences } from "../services/preferences";

export const preferences = ref<Preferences>({ ...DEFAULT_PREFERENCES });
export const preferencesLoaded = ref(false);

export async function loadSharedPreferences(): Promise<void> {
  try {
    preferences.value = await fetchPreferences();
  } catch {
    // defaults stay in place
  } finally {
    preferencesLoaded.value = true;
  }
}
