import { afterEach, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import { useShortcutReconciliation } from "../composables/useShortcutReconciliation";
import {
  preferences,
  preferencesLoaded,
  preferencesError,
  resetSharedPreferences,
} from "../state/preferences";
import {
  registerPluginShortcut,
  retainPluginShortcuts,
  shortcutBinding,
} from "../state/shortcuts";
import {
  shortcutConflictNotices,
  shortcutPersistenceError,
  shortcutSaveRetry,
  dismissShortcutConflict,
} from "../state/shortcutNotices";

let stop: (() => void) | undefined;
afterEach(() => {
  stop?.();
  stop = undefined;
  resetSharedPreferences();
  retainPluginShortcuts(new Set());
  vi.unstubAllGlobals();
});
async function settle() {
  await nextTick();
  for (let index = 0; index < 12; index++) await Promise.resolve();
  await nextTick();
}
function storage() {
  let saved = { ...preferences.value };
  const fetch = vi.fn(async (_url: string, options: RequestInit) => {
    saved = { ...saved, ...JSON.parse(String(options.body)) };
    return new Response(JSON.stringify(saved));
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}
const id = "plugin:example.keys:conflict";
function register() {
  return registerPluginShortcut("example.keys", {
    id: "conflict",
    label: "New conflict",
    keys: ["CtrlOrMeta+K"],
  });
}

it("waits for account preferences, persists blocked discovery once, and does not repeatedly notify on refresh", async () => {
  const fetch = storage();
  stop = useShortcutReconciliation();
  register();
  await settle();
  expect(fetch).not.toHaveBeenCalled();
  preferencesLoaded.value = true;
  await settle();
  expect(preferences.value.keyboard_shortcut_overrides[id].enabled).toBe(false);
  expect(shortcutBinding(id)?.enabled).toBe(false);
  expect(shortcutConflictNotices.value.map((item) => item.id)).toEqual([id]);
  expect(fetch).toHaveBeenCalledTimes(1);
  dismissShortcutConflict(id);
  register();
  await settle();
  expect(shortcutConflictNotices.value).toEqual([]);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("keeps a blocked binding disabled after removal of its owner", async () => {
  storage();
  preferencesLoaded.value = true;
  stop = useShortcutReconciliation();
  register();
  await settle();
  preferences.value = {
    ...preferences.value,
    keyboard_shortcut_overrides: {
      ...preferences.value.keyboard_shortcut_overrides,
      "app.search": { enabled: false },
    },
  };
  await settle();
  expect(shortcutBinding(id)?.activeKeys).toEqual([]);
});

it("shows a retryable account-save error while preserving local disabling and clears notices on logout", async () => {
  const fetch = vi.fn().mockRejectedValueOnce(new Error("Offline"));
  vi.stubGlobal("fetch", fetch);
  register();
  preferencesLoaded.value = true;
  stop = useShortcutReconciliation();
  await settle();
  expect(shortcutBinding(id)?.enabled).toBe(false);
  expect(shortcutPersistenceError.value).toContain("Retry");
  fetch.mockResolvedValueOnce(new Response(JSON.stringify(preferences.value)));
  shortcutSaveRetry.value++;
  await settle();
  expect(shortcutPersistenceError.value).toBe("");
  resetSharedPreferences();
  await settle();
  expect(shortcutConflictNotices.value).toEqual([]);
});

it("does not replace saved bindings when loading the account failed", async () => {
  const fetch = storage();
  preferencesLoaded.value = true;
  preferencesError.value = "Server unavailable";
  stop = useShortcutReconciliation();
  register();
  await settle();
  expect(fetch).not.toHaveBeenCalled();
  expect(shortcutConflictNotices.value).toEqual([]);
});
