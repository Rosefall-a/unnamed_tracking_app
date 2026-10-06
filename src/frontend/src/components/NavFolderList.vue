<script setup lang="ts" generic="T extends NavigationFolderEntry">
import { computed } from "vue";
import AppIcon from "./AppIcon.vue";
import {
  navigationFolderNodes,
  type NavigationFolderEntry,
} from "../utils/pluginPlacement";

const props = defineProps<{
  entries: T[];
  activeIds?: string[];
  collapsed?: boolean;
}>();
defineSlots<{ default(props: { entry: T }): unknown }>();
const nodes = computed(() => navigationFolderNodes(props.entries));
</script>

<template>
  <div class="nav-folder-list">
    <template v-for="node in nodes" :key="node.id">
      <slot v-if="node.kind === 'entry'" :entry="node.entry" />
      <template v-else-if="collapsed">
        <template v-for="entry in node.entries" :key="entry.id">
          <slot :entry="entry" />
        </template>
      </template>
      <details
        v-else
        class="nav-folder"
        :open="node.entries.some((entry) => activeIds?.includes(entry.id))"
      >
        <summary class="nav-folder-label">
          <AppIcon name="folder" :size="17" />
          <span>{{ node.label }}</span>
          <AppIcon class="nav-folder-chevron" name="chevron" :size="14" />
        </summary>
        <div class="nav-folder-contents">
          <NavFolderList :entries="node.entries" :active-ids="activeIds">
            <template #default="{ entry }"><slot :entry="entry" /></template>
          </NavFolderList>
        </div>
      </details>
    </template>
  </div>
</template>

<style scoped>
.nav-folder-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.nav-folder-label {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 10px 12px;
  border-radius: var(--ui-radius-row);
  color: var(--ui-dim);
  cursor: pointer;
  font-size: 14px;
  list-style: none;
}
.nav-folder-label::-webkit-details-marker {
  display: none;
}
.nav-folder-label:hover {
  color: var(--ui-text);
  background: var(--ui-surface-2);
}
.nav-folder-label:focus-visible {
  outline: 2px solid var(--ui-accent);
  outline-offset: 2px;
}
.nav-folder-label > span {
  overflow-wrap: anywhere;
}
.nav-folder-chevron {
  margin-left: auto;
  flex-shrink: 0;
}
.nav-folder[open] > summary .nav-folder-chevron {
  transform: rotate(90deg);
}
.nav-folder-contents {
  padding-left: 12px;
  border-left: 1px solid var(--ui-border);
  margin-left: 12px;
}
</style>
