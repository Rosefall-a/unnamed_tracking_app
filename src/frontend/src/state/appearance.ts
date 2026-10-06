import { ref, watch } from "vue";
import { fetchAppearanceSettings } from "../services/appearanceSettings";
import type { AppearanceSettings } from "../services/appearanceSettings";
import { currentUser } from "./auth";

// loaded once at app boot (see router/index.ts), not per-card, GameCard.vue
// renders hundreds of times and reads this shared ref rather than each
// making its own request
export const appearanceSettings = ref<AppearanceSettings | null>(null);
export const appearanceLoaded = ref(false);
let generation = 0;

export function resetAppearanceSettings(): void {
  generation++;
  appearanceSettings.value = null;
  appearanceLoaded.value = false;
}

watch(() => currentUser.value?.id, resetAppearanceSettings, { flush: "sync" });

export async function loadAppearanceSettings() {
  const requestGeneration = generation;
  const accountId = currentUser.value?.id;
  try {
    const result = await fetchAppearanceSettings();
    if (requestGeneration !== generation || currentUser.value?.id !== accountId)
      return;
    appearanceSettings.value = result;
  } catch {
    // a failed fetch just means no badge customization, cards render
    // with default appearance rather than blocking navigation
  } finally {
    if (requestGeneration === generation && currentUser.value?.id === accountId)
      appearanceLoaded.value = true;
  }
}
