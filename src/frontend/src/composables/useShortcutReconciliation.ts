import { watch } from "vue";
import { shortcutDefinitions } from "../state/shortcuts";
import {
  preferences,
  preferencesLoaded,
  preferencesError,
} from "../state/preferences";
import {
  clearShortcutNotices,
  notifyShortcutConflicts,
  shortcutPersistenceError,
  shortcutSaveRetry,
} from "../state/shortcutNotices";
import { queuePreferences } from "../services/preferences";
import {
  reconcileShortcutOverrides,
  type ShortcutOverride,
} from "../utils/shortcutResolution";

/** Account-scoped discovery persists priority and blocked state across reloads. */
export function useShortcutReconciliation(): () => void {
  let accountGeneration = 0;
  async function persist(overrides: Record<string, ShortcutOverride>) {
    const account = accountGeneration;
    try {
      const result = await queuePreferences({
        keyboard_shortcut_overrides: overrides,
      });
      if (account !== accountGeneration) return;
      if (result.latest) preferences.value = result.prefs;
      shortcutPersistenceError.value = "";
    } catch {
      if (account === accountGeneration)
        shortcutPersistenceError.value =
          "Shortcut changes are active here but could not be saved to your account. Retry before reloading.";
    }
  }
  const stop = watch(
    [
      preferencesLoaded,
      preferencesError,
      shortcutDefinitions,
      () => preferences.value.keyboard_shortcut_overrides,
    ],
    ([loaded, error]) => {
      if (!loaded) {
        accountGeneration++;
        clearShortcutNotices();
        return;
      }
      if (error) return;
      const current = preferences.value.keyboard_shortcut_overrides;
      const result = reconcileShortcutOverrides(
        shortcutDefinitions.value,
        current,
      );
      if (JSON.stringify(result.overrides) === JSON.stringify(current)) return;
      notifyShortcutConflicts(result.disabled);
      preferences.value = {
        ...preferences.value,
        keyboard_shortcut_overrides: result.overrides,
      };
      void persist(result.overrides);
    },
    { immediate: true },
  );
  const stopRetry = watch(shortcutSaveRetry, () => {
    if (preferencesLoaded.value && !preferencesError.value)
      void persist(preferences.value.keyboard_shortcut_overrides);
  });
  return () => {
    accountGeneration++;
    stop();
    stopRetry();
    clearShortcutNotices();
  };
}
