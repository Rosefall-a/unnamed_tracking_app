<script setup lang="ts">
import { ref, watch } from "vue";
import SegmentedControl from "./SegmentedControl.vue";
import ToggleButton from "./ToggleButton.vue";
import { sidebarMode } from "../../state/sidebarMode";
import { preferences } from "../../state/preferences";
import { queuePreferences } from "../../services/preferences";
import type { SidebarMode } from "../../state/sidebarMode";

type ViewMode = "cards" | "list" | "detail";
type SortBy =
  "name" | "recent" | "rating" | "playtime" | "last_played" | "priority";

const defaultViewMode = ref<ViewMode>(
  (localStorage.getItem("gameLibraryViewMode") as ViewMode) || "cards",
);
const defaultSort = ref<SortBy>(
  (localStorage.getItem("gameLibraryDefaultSort") as SortBy) || "name",
);
const compactMode = ref(localStorage.getItem("compactMode") === "true");
const weeklyDigestEnabled = ref(
  localStorage.getItem("weeklyDigestEnabled") !== "false",
);
const highContrastMode = ref(
  localStorage.getItem("highContrastMode") === "true",
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
const sidebarModeOptions = [
  { value: "overlay", label: "Overlay" },
  { value: "pinned", label: "Pinned open" },
  { value: "rail", label: "Icon rail" },
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

watch(defaultViewMode, (mode) =>
  localStorage.setItem("gameLibraryViewMode", mode),
);
watch(defaultSort, (sort) =>
  localStorage.setItem("gameLibraryDefaultSort", sort),
);
watch(compactMode, (enabled) => {
  localStorage.setItem("compactMode", String(enabled));
  document.documentElement.classList.toggle("compact", enabled);
});
watch(weeklyDigestEnabled, (enabled) =>
  localStorage.setItem("weeklyDigestEnabled", String(enabled)),
);
watch(highContrastMode, (enabled) => {
  localStorage.setItem("highContrastMode", String(enabled));
  document.documentElement.classList.toggle("high-contrast", enabled);
});
</script>

<template>
  <section class="settings-section">
    <h2>User interface</h2>
    <p class="section-hint">
      Defaults applied the next time the Games page opens.
    </p>

    <div class="field">
      <span>Default view mode</span>
      <SegmentedControl
        :model-value="defaultViewMode"
        :options="viewModeOptions"
        @update:model-value="defaultViewMode = $event as ViewMode"
      />
    </div>

    <div class="field">
      <span>Default sort</span>
      <SegmentedControl
        :model-value="defaultSort"
        :options="sortOptions"
        @update:model-value="defaultSort = $event as SortBy"
      />
    </div>

    <div class="field">
      <span>Sidebar</span>
      <SegmentedControl
        :model-value="sidebarMode"
        :options="sidebarModeOptions"
        @update:model-value="sidebarMode = $event as SidebarMode"
      />
      <span class="field-hint">
        <strong>Overlay</strong>: hidden until you open it, floats over the
        page. <strong>Pinned open</strong>: always visible at full width.
        <strong>Icon rail</strong>: a thin strip of icons, expands on hover.
      </span>
    </div>

    <div class="field">
      <span>Franchise collections</span>
      <SegmentedControl
        :model-value="preferences.collections_auto"
        :options="autoOptions"
        @update:model-value="setAuto"
      />
      <span class="field-hint">
        Syncing a library files each game into a collection for its series and
        one for where it came from. <strong>Own tab</strong>: they get a
        Franchises tab on Collections and stay out of your own list.
        <strong>With mine</strong>: they are listed with your own.
        <strong>Hidden</strong>: they are not shown at all.
      </span>
      <span v-if="autoError" class="field-hint error">{{ autoError }}</span>
    </div>

    <ToggleButton v-model="compactMode" label="Compact mode">
      <strong>Compact mode</strong>: tighter spacing across the app
    </ToggleButton>

    <ToggleButton v-model="weeklyDigestEnabled" label="Weekly digest">
      <strong>Weekly digest</strong>: a weekly recap card on Home showing games
      played, achievements unlocked and metadata changes from the last 7 days
    </ToggleButton>

    <ToggleButton v-model="highContrastMode" label="High contrast">
      <strong>High contrast</strong>: brighter secondary text, stronger borders,
      and a bolder keyboard focus ring across the app
    </ToggleButton>
  </section>
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
