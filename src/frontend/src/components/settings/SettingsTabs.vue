<script setup lang="ts">
export interface SettingsTab {
  id: string;
  label: string;
  badge?: number;
}

defineProps<{ tabs: SettingsTab[]; modelValue: string }>();
defineEmits<{ "update:modelValue": [id: string] }>();
</script>

<template>
  <div class="settings-tabs" role="tablist">
    <button
      v-for="t in tabs"
      :key="t.id"
      type="button"
      role="tab"
      class="settings-tab"
      :class="{ active: modelValue === t.id }"
      :aria-selected="modelValue === t.id"
      @click="$emit('update:modelValue', t.id)"
    >
      {{ t.label }}
      <span v-if="t.badge" class="tab-badge">{{ t.badge }}</span>
    </button>
  </div>
</template>

<style scoped>
.settings-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 0 0 22px;
  border-bottom: 1px solid var(--ui-border);
}
.settings-tab {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  color: var(--ui-dim-3);
  font: inherit;
  font-size: 0.9rem;
  font-weight: 600;
  padding: 10px 14px;
  cursor: pointer;
  transition:
    color 0.15s ease,
    border-color 0.15s ease;
}
.tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  margin-left: 6px;
  padding: 0 4px;
  box-sizing: border-box;
  border-radius: 999px;
  background: rgba(229, 115, 115, 0.16);
  color: #fca5a5;
  font-size: 10.5px;
  font-weight: 700;
  vertical-align: 1px;
}
.settings-tab:hover {
  color: var(--ui-heading);
}
.settings-tab.active {
  color: var(--ui-accent);
  border-bottom-color: var(--ui-accent);
}
</style>
