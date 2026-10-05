<script setup lang="ts">
import ShortcutBindings from "./ShortcutBindings.vue";
import { shortcutHint } from "../../state/shortcuts";
import { startQuickTour } from "../../state/quickTour";
</script>

<template>
  <section class="settings-section">
    <h2>Keyboard Shortcuts</h2>
    <p class="hint">
      <template v-if="shortcutHint('app.help')"
        >Press <kbd>{{ shortcutHint("app.help") }}</kbd> to show shortcuts for
        the current page first.</template
      >
      Expand or collapse any section. Navigation works across the app; page
      shortcuts work where their controls are available. Shortcuts pause while
      you type or use a dialog.
    </p>
    <ShortcutBindings />
    <button type="button" class="ui-btn ui-btn-ghost" @click="startQuickTour">
      Replay guided tour
    </button>
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
