<script setup lang="ts">
// The switcher between the media libraries and Collections. Calendar and Statistics
// are not part of Media, they have their own sidebar entries.
import SegmentedTabs from "./SegmentedTabs.vue";
import type { SegmentOption } from "./SegmentedTabs.vue";

defineProps<{
  active: "movie" | "tv" | "anime" | "lists";
}>();

// Icons are the sidebar's own Movies / TV / Anime icons, and the same
// Collections icon the Games bar uses.
const OPTIONS: SegmentOption[] = [
  {
    value: "movie",
    label: "Movies",
    to: "/movies",
    icon: '<rect x="3" y="3" width="18" height="18" rx="2" /><line x1="3" y1="8" x2="21" y2="8" /><rect x="5.5" y="4.5" width="1.6" height="1.6" fill="currentColor" stroke="none" /><rect x="9.8" y="4.5" width="1.6" height="1.6" fill="currentColor" stroke="none" /><rect x="14.1" y="4.5" width="1.6" height="1.6" fill="currentColor" stroke="none" /><rect x="18.4" y="4.5" width="1.6" height="1.6" fill="currentColor" stroke="none" />',
  },
  {
    value: "tv",
    label: "TV Shows",
    to: "/tv",
    icon: '<rect x="2" y="5" width="20" height="13" rx="2" /><path d="M8 21h8M12 18v3" />',
  },
  {
    value: "anime",
    label: "Anime",
    to: "/anime",
    icon: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" /><path d="M19 15l0.7 2 2 0.7-2 0.7-0.7 2-0.7-2-2-0.7 2-0.7z" />',
  },
  {
    value: "lists",
    label: "Collections",
    to: "/media/collections",
    icon: '<path d="M4 7l8-4 8 4-8 4-8-4z" /><path d="M4 12l8 4 8-4M4 17l8 4 8-4" />',
  },
];
</script>

<template>
  <SegmentedTabs
    :options="OPTIONS"
    :model-value="active"
    aria-label="Library"
  />
</template>
