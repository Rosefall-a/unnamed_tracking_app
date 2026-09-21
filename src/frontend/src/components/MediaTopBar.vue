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
import { preferences } from "../state/preferences";
import { updatePreferences } from "../services/preferences";
import type { Preferences } from "../services/preferences";

const props = defineProps<{
  active: "movie" | "tv" | "anime" | "lists";
}>();

// which spelling anime titles are shown in; only anime titles have one
const LANGUAGES: SegmentOption[] = [
  { value: "english", label: "English" },
  { value: "romaji", label: "Romaji" },
  { value: "native", label: "日本語" },
];
const showLanguage = computed(
  () => props.active === "anime" || props.active === "lists",
);
async function setLanguage(value: string) {
  const previous = preferences.value;
  preferences.value = {
    ...previous,
    title_language: value as Preferences["title_language"],
  };
  try {
    preferences.value = await updatePreferences({
      title_language: value as Preferences["title_language"],
    });
  } catch {
    preferences.value = previous;
  }
}

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
        v-if="showLanguage"
        :options="LANGUAGES"
        :model-value="preferences.title_language"
        aria-label="Title language"
        @update:model-value="setLanguage"
      />
      <SegmentedTabs
        :options="LISTS"
        :model-value="listsActive"
        aria-label="Lists"
      />
    </template>
  </AppTopBar>
</template>
