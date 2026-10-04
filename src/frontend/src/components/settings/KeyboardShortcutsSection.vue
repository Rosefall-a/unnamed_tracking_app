<script setup lang="ts">
import { useRoute } from "vue-router";
import ShortcutGroups from "../ShortcutGroups.vue";
const route = useRoute();
</script>

<template>
  <section class="settings-section">
    <h2>Keyboard Shortcuts</h2>
    <p class="hint">
      Press <kbd>?</kbd> to show shortcuts for the current page first. Expand or
      collapse any section. Navigation works across the app; page shortcuts work
      where their controls are available. Shortcuts pause while you type or use
      a dialog.
    </p>
    <ShortcutGroups :path="route.path" />
  </section>
</template>

<style scoped>
.settings-section h2 {
  margin: 0 0 12px;
  font: var(--ui-weight-heading) var(--ui-font-heading)/1.4
    var(--ui-font-family);
  color: var(--ui-text);
}
.hint {
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
  line-height: 1.6;
  margin: 0 0 20px;
}
kbd {
  padding: 3px 8px;
  border: 1px solid var(--ui-border-strong);
  border-radius: 6px;
  background: var(--ui-surface-2);
  color: var(--ui-text);
  font-family: ui-monospace, monospace;
}
</style>
