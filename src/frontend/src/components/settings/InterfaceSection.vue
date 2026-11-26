<script setup lang="ts">
import { getUi, setUi } from "../../state/uiState";
import SettingsCard from "./SettingsCard.vue";
import SettingsRow from "./SettingsRow.vue";
import SettingsSwitch from "./SettingsSwitch.vue";
import { ref, watch } from "vue";
import SegmentedControl from "./SegmentedControl.vue";
import { preferences } from "../../state/preferences";
import { queuePreferences } from "../../services/preferences";
import type { TimeToBeatStyle } from "../../services/preferences";
import { TIME_TO_BEAT_STYLES } from "../../utils/timeToBeat";

// display: the Compact and High contrast switches, shown on Appearance;
// views (the default): the library defaults on Library views
withDefaults(defineProps<{ part?: "views" | "display" }>(), { part: "views" });

type ViewMode = "cards" | "list" | "detail";
type SortBy =
  "name" | "recent" | "rating" | "playtime" | "last_played" | "priority";

const defaultViewMode = ref<ViewMode>(
  getUi<ViewMode>("gameLibraryViewMode", "cards") || "cards",
);
const defaultSort = ref<SortBy>(
  getUi<SortBy>("gameLibraryDefaultSort", "name") || "name",
);
const compactMode = ref(
  String(getUi<unknown>("compactMode", false)) === "true",
);
const weeklyDigestEnabled = ref(
  String(getUi<unknown>("weeklyDigestEnabled", true)) !== "false",
);
const highContrastMode = ref(
  String(getUi<unknown>("highContrastMode", false)) === "true",
);

const viewModeOptions = [
  { value: "list", label: "List" },
  { value: "cards", label: "Shelves" },
  { value: "detail", label: "List + preview" },
];
const sortOptions = [
  { value: "name", label: "Name" },
  { value: "recent", label: "Recently added" },
  { value: "rating", label: "Rating" },
  { value: "playtime", label: "Most played" },
  { value: "last_played", label: "Recently played" },
  { value: "priority", label: "Priority" },
];
const autoOptions = [
  { value: "tab", label: "Own tab" },
  { value: "mixed", label: "With mine" },
  { value: "hidden", label: "Hidden" },
];
const autoError = ref<string | null>(null);
async function setAuto(value: string) {
  const mode = value as "tab" | "mixed" | "hidden";
  const before = preferences.value.collections_auto;
  preferences.value = { ...preferences.value, collections_auto: mode };
  try {
    await queuePreferences({ collections_auto: mode });
    autoError.value = null;
  } catch (e) {
    preferences.value = { ...preferences.value, collections_auto: before };
    autoError.value =
      e instanceof Error ? e.message : "Could not save that choice.";
  }
}

const timeError = ref<string | null>(null);
async function setTimeStyle(value: string) {
  const style = value as TimeToBeatStyle;
  const before = preferences.value.time_to_beat_style;
  preferences.value = { ...preferences.value, time_to_beat_style: style };
  try {
    await queuePreferences({ time_to_beat_style: style });
    timeError.value = null;
  } catch (e) {
    preferences.value = { ...preferences.value, time_to_beat_style: before };
    timeError.value =
      e instanceof Error ? e.message : "Could not save that choice.";
  }
}

watch(defaultViewMode, (mode) => setUi("gameLibraryViewMode", mode));
watch(defaultSort, (sort) => setUi("gameLibraryDefaultSort", sort));
watch(compactMode, (enabled) => {
  setUi("compactMode", enabled);
  document.documentElement.classList.toggle("compact", enabled);
});
watch(weeklyDigestEnabled, (enabled) => setUi("weeklyDigestEnabled", enabled));
watch(highContrastMode, (enabled) => {
  setUi("highContrastMode", enabled);
  document.documentElement.classList.toggle("high-contrast", enabled);
});
</script>

<template>
  <SettingsCard v-if="part === 'display'" title="Display">
    <SettingsRow label="Compact mode" hint="Tighter spacing across the app">
      <SettingsSwitch v-model="compactMode" label="Compact mode" />
    </SettingsRow>
    <SettingsRow
      label="High contrast"
      hint="Brighter secondary text, stronger borders and a bolder focus ring"
    >
      <SettingsSwitch v-model="highContrastMode" label="High contrast" />
    </SettingsRow>
  </SettingsCard>
  <template v-else>
    <SettingsCard title="Games" description="What the Games page starts on.">
      <SettingsRow label="View">
        <SegmentedControl
          :model-value="defaultViewMode"
          :options="viewModeOptions"
          @update:model-value="defaultViewMode = $event as ViewMode"
        />
      </SettingsRow>
      <SettingsRow label="Sort" stack>
        <SegmentedControl
          :model-value="defaultSort"
          :options="sortOptions"
          @update:model-value="defaultSort = $event as SortBy"
        />
      </SettingsRow>
      <SettingsRow
        label="Time to beat"
        hint="Used on game pages, sorts, the picker, Home and backlog hours"
        stack
      >
        <SegmentedControl
          :model-value="preferences.time_to_beat_style"
          :options="TIME_TO_BEAT_STYLES"
          @update:model-value="setTimeStyle"
        />
      </SettingsRow>
      <p v-if="timeError" class="st-error">{{ timeError }}</p>
      <SettingsRow
        label="Franchise collections"
        hint="The series and source collections a sync makes. Own tab keeps them out of your list, With mine lists them with yours."
        stack
      >
        <SegmentedControl
          :model-value="preferences.collections_auto"
          :options="autoOptions"
          @update:model-value="setAuto"
        />
      </SettingsRow>
      <p v-if="autoError" class="st-error">{{ autoError }}</p>
    </SettingsCard>
    <SettingsCard title="Everywhere">
      <SettingsRow
        label="Weekly digest on Home"
        hint="Games played, achievements and changes from the last 7 days"
      >
        <SettingsSwitch v-model="weeklyDigestEnabled" label="Weekly digest" />
      </SettingsRow>
    </SettingsCard>
  </template>
</template>

<style scoped>
.settings-section h2 {
  margin: 0 0 8px;
  padding-left: 12px;
  border-left: 3px solid var(--ui-accent);
  font-size: 1rem;
  color: var(--ui-heading);
}
.section-hint {
  color: var(--ui-dim-3);
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 16px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--ui-text-soft);
  margin-bottom: 18px;
}
.field-hint {
  color: var(--ui-dim-2);
  font-size: 0.78rem;
  line-height: 1.5;
}
.field-hint.error {
  color: var(--ui-error-text);
}
</style>
