<script setup lang="ts">
// The Media-area bar: AppTopBar with the Movies / TV Shows / Anime
// switcher on the left, and on the right whatever the page adds (its
// `actions` slot) followed by the Lists button. The Lists button is the
// same control in the same place on every Media page, and lights up on
// Lists and on a single list.
import { computed } from "vue";
import { useRoute } from "vue-router";
import AppTopBar from "./AppTopBar.vue";
import MediaKindSwitch from "./MediaKindSwitch.vue";
import SegmentedTabs from "./SegmentedTabs.vue";
import type { SegmentOption } from "./SegmentedTabs.vue";

defineProps<{
  active: "movie" | "tv" | "anime" | "lists";
}>();

const route = useRoute();
const LISTS: SegmentOption[] = [
  {
    value: "lists",
    label: "Lists",
    to: "/lists",
    icon: '<line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" /><line x1="8" y1="18" x2="21" y2="18" /><line x1="3" y1="6" x2="3.01" y2="6" /><line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" />',
  },
];
const listsActive = computed(() =>
  route.path.startsWith("/lists") ? "lists" : "",
);
</script>

<template>
  <AppTopBar>
    <MediaKindSwitch :active="active" />
    <template #actions>
      <slot name="actions" />
      <SegmentedTabs
        :options="LISTS"
        :model-value="listsActive"
        aria-label="Lists"
      />
    </template>
  </AppTopBar>
</template>
