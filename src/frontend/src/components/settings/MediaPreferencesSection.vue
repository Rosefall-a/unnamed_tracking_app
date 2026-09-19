<script setup lang="ts">
// Defaults for the Movies, TV and Anime libraries, Lists and Statistics.
// Saved on the server as they are changed.
import { ref, onMounted } from "vue";
import SegmentedControl from "./SegmentedControl.vue";
import ToggleButton from "./ToggleButton.vue";
import {
  DEFAULT_PREFERENCES,
  fetchPreferences,
  updatePreferences,
} from "../../services/preferences";
import type { Preferences } from "../../services/preferences";
import { preferences as sharedPreferences } from "../../state/preferences";

const prefs = ref<Preferences>({ ...DEFAULT_PREFERENCES });
const loaded = ref(false);
const error = ref<string | null>(null);
const savedNote = ref("");

onMounted(async () => {
  try {
    prefs.value = await fetchPreferences();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load settings.";
  } finally {
    loaded.value = true;
  }
});

async function change(changes: Partial<Preferences>) {
  const previous = { ...prefs.value };
  prefs.value = { ...prefs.value, ...changes };
  error.value = null;
  try {
    prefs.value = await updatePreferences(changes);
    sharedPreferences.value = prefs.value;
    savedNote.value = "Saved";
    setTimeout(() => (savedNote.value = ""), 1500);
  } catch (e) {
    prefs.value = previous;
    error.value = e instanceof Error ? e.message : "Failed to save.";
  }
}

const layoutOptions = [
  { value: "list", label: "List" },
  { value: "shelf", label: "Shelf" },
  { value: "board", label: "Board" },
];
const listSortOptions = [
  { value: "name", label: "Name" },
  { value: "count", label: "Most titles" },
  { value: "recent", label: "Recently updated" },
];
</script>

<template>
  <section class="settings-section">
    <h2>Media Preferences</h2>
    <p class="section-hint">
      Defaults for Movies, TV Shows, Anime, Lists and Statistics.
      <span v-if="savedNote" class="saved">{{ savedNote }}</span>
    </p>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="field">
      <span>Library layout</span>
      <SegmentedControl
        :model-value="prefs.library_default_layout"
        :options="layoutOptions"
        @update:model-value="
          change({
            library_default_layout:
              $event as Preferences['library_default_layout'],
          })
        "
      />
      <small>Used until you pick a layout on a library page yourself.</small>
    </div>
    <div class="field">
      <span>Lists sort</span>
      <SegmentedControl
        :model-value="prefs.lists_default_sort"
        :options="listSortOptions"
        @update:model-value="
          change({
            lists_default_sort: $event as Preferences['lists_default_sort'],
          })
        "
      />
    </div>
    <ToggleButton
      :model-value="prefs.stats_include_plan"
      label="Count Plan to Watch in Statistics"
      :disabled="!loaded"
      @update:model-value="change({ stats_include_plan: $event })"
    >
      <strong>Count Plan to Watch in Statistics</strong>: include titles you
      have not started in title totals, genre and score charts. Watch time only
      ever counts episodes you marked watched, whatever this is set to.
    </ToggleButton>
  </section>
</template>

<style scoped>
.settings-section h2 {
  margin: 0 0 8px;
  padding-left: 12px;
  border-left: 3px solid #d68a34;
  font-size: 1rem;
  color: #fff;
}
.section-hint {
  color: #9c9c9c;
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 14px;
}
.saved {
  color: #6fbf73;
  margin-left: 8px;
  font-weight: 700;
}
.error {
  color: #e57373;
  font-size: 0.82rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 14px 0;
  font-size: 0.82rem;
  color: #ccc;
}
.field small {
  color: #666;
}
.settings-section :deep(.toggle-button) {
  margin: 12px 0;
}
</style>
