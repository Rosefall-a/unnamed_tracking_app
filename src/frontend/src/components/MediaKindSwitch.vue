<script setup lang="ts">
// The switcher between the media libraries and Lists. Calendar and Statistics
// are not part of Media, they have their own sidebar entries.
import SegmentedTabs from "./SegmentedTabs.vue";
import type { SegmentOption } from "./SegmentedTabs.vue";

defineProps<{
  active: "movie" | "tv" | "anime" | "lists";
}>();

const OPTIONS: SegmentOption[] = [
  { value: "movie", label: "Movies", to: "/movies" },
  { value: "tv", label: "TV Shows", to: "/tv" },
  { value: "anime", label: "Anime", to: "/anime" },
  { value: "lists", label: "Lists", to: "/lists" },
];
</script>

<template>
  <SegmentedTabs
    :options="OPTIONS"
    :model-value="active"
    aria-label="Library"
  />
</template>
