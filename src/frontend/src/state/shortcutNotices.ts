import { ref } from "vue";
import type { ResolvedShortcut } from "../utils/shortcutResolution";

export const shortcutConflictNotices = ref<ResolvedShortcut[]>([]);
export const shortcutPersistenceError = ref("");
export const shortcutSaveRetry = ref(0);

export function notifyShortcutConflicts(items: ResolvedShortcut[]): void {
  for (const item of items) {
    if (shortcutConflictNotices.value.some((notice) => notice.id === item.id))
      continue;
    shortcutConflictNotices.value.push(item);
  }
  shortcutConflictNotices.value = shortcutConflictNotices.value.slice(-20);
}

export function dismissShortcutConflict(id: string): void {
  shortcutConflictNotices.value = shortcutConflictNotices.value.filter(
    (item) => item.id !== id,
  );
}

export function clearShortcutNotices(): void {
  shortcutConflictNotices.value = [];
  shortcutPersistenceError.value = "";
}
