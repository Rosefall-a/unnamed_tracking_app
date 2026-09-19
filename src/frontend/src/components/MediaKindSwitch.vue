<script setup lang="ts">
// The switcher between the three libraries. Lists is not in here: it has
// its own button at the end of the top bar's right-hand group (see
// MediaTopBar.vue), the same on every Media page. Calendar and Statistics
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
];
</script>

<template>
  <SegmentedTabs :options="OPTIONS" :model-value="active" aria-label="Library" />
</template>
