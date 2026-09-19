<script setup lang="ts">
// The one segmented pill control used everywhere a small set of options
// is switched: the Movies / TV / Anime switcher, the Lists button, the
// library layout tabs, and the tab rows on Calendar, Statistics,
// Notifications and Lists. Same 4px container, 30px options, 7px option
// radius and type size every time. An option is a button, or a link when
// it has `to`. `icon` is inner SVG markup from our own code, drawn 15px.
export interface SegmentOption {
  value: string;
  label: string;
  icon?: string;
  count?: number;
  to?: string;
  title?: string;
}

defineProps<{
  options: SegmentOption[];
  modelValue?: string;
  ariaLabel?: string;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
</script>

<template>
  <div class="seg" role="group" :aria-label="ariaLabel">
    <template v-for="o in options" :key="o.value">
      <RouterLink
        v-if="o.to"
        :to="o.to"
        class="seg-tab"
        :class="{ active: modelValue === o.value }"
        :title="o.title"
      >
        <svg
          v-if="o.icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          v-html="o.icon"
        ></svg>
        {{ o.label }}
        <span v-if="o.count" class="seg-count">{{ o.count }}</span>
      </RouterLink>
      <button
        v-else
        type="button"
        class="seg-tab"
        :class="{ active: modelValue === o.value }"
        :title="o.title"
        @click="emit('update:modelValue', o.value)"
      >
        <svg
          v-if="o.icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          v-html="o.icon"
        ></svg>
        {{ o.label }}
        <span v-if="o.count" class="seg-count">{{ o.count }}</span>
      </button>
    </template>
  </div>
</template>

<style scoped>
.seg {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 4px;
  background: var(--ui-surface);
  border-radius: var(--ui-radius-row);
}
.seg-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  box-sizing: border-box;
  height: 30px;
  padding: 0 14px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--ui-dim);
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
  text-decoration: none;
  cursor: pointer;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.seg-tab:hover {
  color: var(--ui-text);
}
.seg-tab.active {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
}
.seg-tab svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  display: block;
}
.seg-count {
  font-size: 0.68rem;
  opacity: 0.7;
}
</style>
