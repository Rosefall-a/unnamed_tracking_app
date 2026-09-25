<script setup lang="ts">
import { SHORTCUT_GROUPS } from "../../utils/shortcuts";
</script>

<template>
  <section class="settings-section">
    <h2>Keyboard Shortcuts</h2>
    <p class="hint">
      Press <kbd>?</kbd> anywhere in the app to open this list as an overlay.
    </p>
    <div v-for="group in SHORTCUT_GROUPS" :key="group.title" class="group">
      <h3>{{ group.title }}</h3>
      <div v-for="s in group.shortcuts" :key="s.label" class="shortcut">
        <kbd>{{ s.keys }}</kbd>
        <span>{{ s.label }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.settings-section h2 {
  margin: 0 0 8px;
  padding-left: 12px;
  border-left: 3px solid #d68a34;
  font-size: 1rem;
  color: #fff;
}
.hint {
  color: #888;
  font-size: 0.85rem;
  margin: 0 0 12px;
}
.group {
  margin-top: 22px;
}
h3 {
  margin: 0 0 8px;
  font-size: 0.85rem;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.shortcut {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 9px 12px;
  border-bottom: 1px solid #232323;
  color: #ddd;
  font-size: 0.9rem;
}
.shortcut kbd {
  min-width: 150px;
}
kbd {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid #3a3a3a;
  border-bottom-width: 2px;
  background: #111;
  color: #eee;
  font: inherit;
  font-size: 0.78rem;
  font-weight: 600;
  white-space: nowrap;
}
</style>
