import { ref } from 'vue'
import { fetchAppearanceSettings } from '../services/appearanceSettings'
import type { AppearanceSettings } from '../services/appearanceSettings'

// loaded once at app boot (see router/index.ts), not per-card — GameCard.vue
// renders hundreds of times and reads this shared ref rather than each
// making its own request
export const appearanceSettings = ref<AppearanceSettings | null>(null)
export const appearanceLoaded = ref(false)

export async function loadAppearanceSettings() {
  try {
    appearanceSettings.value = await fetchAppearanceSettings()
  } catch {
    // a failed fetch just means no badge customization — cards render
    // with default appearance rather than blocking navigation
  } finally {
    appearanceLoaded.value = true
  }
}
