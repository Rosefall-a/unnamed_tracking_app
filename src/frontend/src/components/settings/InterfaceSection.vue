<script setup lang="ts">
import { ref, watch } from "vue";
import SegmentedControl from "./SegmentedControl.vue";
import ToggleButton from "./ToggleButton.vue";
import { sidebarMode } from "../../state/sidebarMode";
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
const weeklyDigestEnabled = ref(
  localStorage.getItem("weeklyDigestEnabled") !== "false",
);

const viewModeOptions = [
  { value: "cards", label: "Cards" },
  { value: "list", label: "List" },
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
  { value: "auto", label: "Auto" },
  { value: "overlay", label: "Overlay" },
  { value: "pinned", label: "Pinned open" },
  { value: "rail", label: "Icon rail" },
];

watch(defaultViewMode, (mode) =>
  localStorage.setItem("gameLibraryViewMode", mode),
);
watch(defaultSort, (sort) =>
  localStorage.setItem("gameLibraryDefaultSort", sort),
);
watch(weeklyDigestEnabled, (enabled) =>
  localStorage.setItem("weeklyDigestEnabled", String(enabled)),
);
</script>

<template>
  <section class="settings-section">
    <h2>User Interface</h2>
    <p class="section-hint">
      These are the defaults used the next time you open the Games page: they
      don't change anything on a page you already have open.
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
        <strong>Auto</strong>: full pane on desktop, icon rail on tablet.
        <strong>Overlay</strong>: hidden until you open it, floats over the
        page. <strong>Pinned open</strong>: always visible at full width.
        <strong>Icon rail</strong>: a thin strip of icons with an expand button.
        Phones always use bottom navigation and a menu. Takes effect immediately
        on this device.
      </span>
    </div>

    <p class="field-hint">
      Theme, density, contrast and motion are now under
      <router-link to="/settings?section=appearance">Appearance</router-link>
      and follow your account between devices.
    </p>

    <ToggleButton v-model="weeklyDigestEnabled" label="Weekly digest">
      <strong>Weekly digest</strong>: a "this week" recap card on the Home Hub
      showing games played, achievements unlocked, and metadata changes over the
      last 7 days
    </ToggleButton>
  </section>
</template>

<style scoped>
.settings-section h2 {
  margin: 0 0 12px;
  font: var(--ui-weight-heading) var(--ui-font-heading)/1.4
    var(--ui-font-family);
  color: var(--ui-text);
}
.section-hint {
  color: var(--ui-dim);
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 16px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--ui-text);
  margin-bottom: 18px;
}
.field-hint {
  color: var(--ui-faint);
  font-size: 0.78rem;
  line-height: 1.5;
}
</style>
