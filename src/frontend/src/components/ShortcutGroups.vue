<script setup lang="ts">
import { computed } from "vue";
import { shortcutGroupsForPath } from "../utils/shortcuts";

const props = defineProps<{ path: string }>();
const groups = computed(() => shortcutGroupsForPath(props.path));
</script>

<template>
  <div class="shortcut-groups" :key="path">
    <details
      v-for="(group, index) in groups"
      :key="group.title"
      :open="index === 0"
      class="shortcut-group"
    >
      <summary>
        {{ group.title
        }}<span v-if="group.current" class="current-page">Current page</span>
      </summary>
      <div class="group-content">
        <div
          v-for="shortcut in group.shortcuts"
          :key="shortcut.keys + shortcut.label"
          class="shortcut-row"
        >
          <span
            >{{ shortcut.label
            }}<small v-if="shortcut.conflict" class="conflict">{{
              shortcut.conflict
            }}</small
            ><small v-else-if="shortcut.disabled">Disabled</small></span
          ><kbd>{{ shortcut.keys }}</kbd>
        </div>
      </div>
    </details>
  </div>
</template>

<style scoped>
.shortcut-groups {
  display: grid;
  gap: 12px;
}
.shortcut-group {
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-row);
  overflow: hidden;
}
summary {
  min-height: var(--ui-control-height);
  padding: 12px 16px;
  cursor: pointer;
  font-weight: var(--ui-weight-heading);
  background: var(--ui-surface-2);
}
.current-page {
  margin-left: 12px;
  color: var(--ui-accent-text);
  font-size: var(--ui-font-small);
  font-weight: 500;
}
.group-content {
  padding: 8px 16px;
}
.shortcut-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 0;
}
.shortcut-row + .shortcut-row {
  border-top: 1px solid var(--ui-border-soft);
}
.shortcut-row span {
  min-width: 0;
  overflow-wrap: anywhere;
}
kbd {
  flex-shrink: 0;
  max-width: 48%;
  padding: 3px 8px;
  border: 1px solid var(--ui-border-strong);
  border-radius: 6px;
  background: var(--ui-surface-2);
  color: var(--ui-text);
  font-family: ui-monospace, monospace;
  font-size: var(--ui-font-small);
  text-align: right;
  white-space: normal;
}
small {
  display: block;
  margin-top: 4px;
  color: var(--ui-dim);
}
.conflict {
  color: var(--ui-warning);
}
</style>
