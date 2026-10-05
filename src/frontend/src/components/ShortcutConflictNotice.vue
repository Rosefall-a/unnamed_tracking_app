<script setup lang="ts">
import { computed } from "vue";
import {
  shortcutConflictNotices,
  shortcutPersistenceError,
  shortcutSaveRetry,
  dismissShortcutConflict,
} from "../state/shortcutNotices";
import { shortcutKeyLabel } from "../utils/shortcutKeys";

const notice = computed(() => shortcutConflictNotices.value[0]);
</script>

<template>
  <Teleport to="body">
    <aside
      v-if="notice || shortcutPersistenceError"
      class="shortcut-notice"
      role="alert"
      aria-live="polite"
    >
      <template v-if="notice">
        <div class="notice-heading">
          <strong>New shortcut could not be added</strong>
          <button
            type="button"
            class="ui-btn ui-btn-ghost"
            aria-label="Dismiss shortcut conflict"
            @click="dismissShortcutConflict(notice.id)"
          >
            ×
          </button>
        </div>
        <p>{{ notice.label }} was disabled because of a conflicting keybind.</p>
        <p v-for="conflict in notice.conflicts" :key="conflict.key">
          <kbd>{{ shortcutKeyLabel(conflict.key) }}</kbd> belongs to
          {{ conflict.label }}. The oldest enabled shortcut stays active.
        </p>
        <RouterLink
          class="ui-btn ui-btn-primary"
          :to="{
            path: '/settings',
            query: { section: 'shortcuts', binding: notice.id },
          }"
          @click="dismissShortcutConflict(notice.id)"
          >Change keys</RouterLink
        >
        <small v-if="shortcutConflictNotices.length > 1"
          >{{ shortcutConflictNotices.length - 1 }} more conflict notices</small
        >
      </template>
      <p v-if="shortcutPersistenceError">{{ shortcutPersistenceError }}</p>
      <button
        v-if="shortcutPersistenceError"
        type="button"
        class="ui-btn ui-btn-ghost"
        @click="shortcutSaveRetry++"
      >
        Retry saving
      </button>
    </aside>
  </Teleport>
</template>

<style scoped>
.shortcut-notice {
  position: fixed;
  z-index: 1100;
  top: calc(env(safe-area-inset-top, 0px) + 16px);
  right: 16px;
  width: min(400px, calc(100vw - 32px));
  box-sizing: border-box;
  padding: var(--ui-space-4);
  display: grid;
  gap: var(--ui-space-3);
  border: 1px solid var(--ui-warning);
  border-radius: var(--ui-radius-card);
  background: var(--ui-popover);
  color: var(--ui-text);
  box-shadow: var(--ui-elevation);
  overflow-wrap: anywhere;
}
.notice-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ui-space-3);
}
.notice-heading button {
  flex-shrink: 0;
}
p {
  margin: 0;
}
small {
  color: var(--ui-dim);
}
@media (max-width: 760px) {
  .shortcut-notice {
    top: calc(env(safe-area-inset-top, 0px) + 64px);
    max-height: calc(
      100dvh - env(safe-area-inset-top, 0px) -
        env(safe-area-inset-bottom, 0px) - 156px
    );
    overflow-y: auto;
  }
}
</style>
