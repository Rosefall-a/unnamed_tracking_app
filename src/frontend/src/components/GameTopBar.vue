<script setup lang="ts">
// The Games-area bar, the counterpart of MediaTopBar: AppTopBar with the
// Games / Collections switcher on the left (the same pill control as the
// Movies / TV / Anime switcher), and on the right whatever the page adds
// through its `actions` slot.
import AppTopBar from "./AppTopBar.vue";
import SegmentedTabs from "./SegmentedTabs.vue";
import type { SegmentOption } from "./SegmentedTabs.vue";

defineProps<{ active: "games" | "collections" }>();

const KINDS: SegmentOption[] = [
  {
    value: "games",
    label: "Games",
    to: "/games",
    icon: '<path d="M6 6h12a3 3 0 0 1 3 3v1l1.3 7a2.2 2.2 0 0 1-4 1.7L17 16H7l-1.3 2.7a2.2 2.2 0 0 1-4-1.7L3 10v-1a3 3 0 0 1 3-3z" /><path d="M7.3 9.3v4M5.3 11.3h4" />',
  },
  {
    value: "collections",
    label: "Collections",
    to: "/collections",
    icon: '<path d="M4 7l8-4 8 4-8 4-8-4z" /><path d="M4 12l8 4 8-4M4 17l8 4 8-4" />',
  },
];
</script>

<template>
  <AppTopBar>
    <SegmentedTabs
      :options="KINDS"
      :model-value="active"
      aria-label="Games area"
    />
    <template #actions>
      <slot name="actions" />
    </template>
  </AppTopBar>
</template>
