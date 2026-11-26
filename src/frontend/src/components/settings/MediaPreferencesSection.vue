<script setup lang="ts">
// Defaults for the Movies, TV and Anime libraries, Lists and Statistics.
// Saved on the server as they are changed.
import { ref, onMounted } from "vue";
import SettingsCard from "./SettingsCard.vue";
import SettingsRow from "./SettingsRow.vue";
import SettingsSwitch from "./SettingsSwitch.vue";
import SegmentedControl from "./SegmentedControl.vue";
import {
  DEFAULT_PREFERENCES,
  fetchPreferences,
  queuePreferences,
} from "../../services/preferences";
import type { Preferences } from "../../services/preferences";
import { preferences as sharedPreferences } from "../../state/preferences";
import { fillAlternateTitles } from "../../services/anime";

const prefs = ref<Preferences>({ ...DEFAULT_PREFERENCES });
const loaded = ref(false);
const error = ref<string | null>(null);
const savedNote = ref("");

onMounted(async () => {
  try {
    prefs.value = await fetchPreferences();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not load settings.";
  } finally {
    loaded.value = true;
  }
});

async function change(changes: Partial<Preferences>) {
  const previous = { ...prefs.value };
  prefs.value = { ...prefs.value, ...changes };
  error.value = null;
  try {
    const { prefs: saved, latest } = await queuePreferences(changes);
    if (latest) {
      prefs.value = saved;
      sharedPreferences.value = saved;
    }
    savedNote.value = "Saved";
    setTimeout(() => (savedNote.value = ""), 1500);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not save.";
    try {
      prefs.value = await fetchPreferences();
    } catch {
      prefs.value = previous;
    }
  }
}

const titleLanguageOptions = [
  { value: "english", label: "Translated (English)" },
  { value: "romaji", label: "Original (romaji)" },
  { value: "native", label: "Japanese" },
];
const fillingTitles = ref(false);
const titlesNote = ref("");
async function lookUpTitles() {
  fillingTitles.value = true;
  titlesNote.value = "";
  try {
    const r = await fillAlternateTitles();
    titlesNote.value = r.checked
      ? `Found the alternate titles for ${r.filled} of ${r.checked} anime.` +
        (r.without_id
          ? ` ${r.without_id} have no AniList or MyAnimeList id, so they can't be looked up.`
          : "") +
        (r.lookup_failed
          ? ` AniList could not be reached for ${r.lookup_failed}: try again later.`
          : "")
      : "Every anime already has its titles.";
  } catch (e) {
    titlesNote.value =
      e instanceof Error ? e.message : "Could not look up titles.";
  } finally {
    fillingTitles.value = false;
  }
}

const layoutOptions = [
  { value: "list", label: "List" },
  { value: "shelf", label: "Shelf" },
  { value: "board", label: "Board" },
];
const listSortOptions = [
  { value: "custom", label: "My order" },
  { value: "name", label: "Name" },
  { value: "count", label: "Most titles" },
  { value: "recent", label: "Recently updated" },
];
</script>

<template>
  <SettingsCard title="Movies, TV and anime">
    <template #actions>
      <span v-if="savedNote" class="saved">{{ savedNote }}</span>
    </template>
    <p v-if="error" class="st-error">{{ error }}</p>
    <SettingsRow
      label="Layout"
      hint="Until a layout is picked on a library page"
    >
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
    </SettingsRow>
    <SettingsRow label="Anime names" stack>
      <template #hint>
        Which spelling is the main name, for example ERASED or Boku dake ga Inai
        Machi. Others show under it. Anime added earlier need Look up titles
        once.
      </template>
      <div class="names">
        <SegmentedControl
          :model-value="prefs.title_language"
          :options="titleLanguageOptions"
          @update:model-value="
            change({
              title_language: $event as Preferences['title_language'],
            })
          "
        />
        <button
          type="button"
          class="st-btn"
          :disabled="fillingTitles"
          @click="lookUpTitles"
        >
          {{ fillingTitles ? "Looking up…" : "Look up titles" }}
        </button>
        <span v-if="titlesNote" class="st-muted">{{ titlesNote }}</span>
      </div>
    </SettingsRow>
    <SettingsRow label="Collection sort">
      <SegmentedControl
        :model-value="prefs.lists_default_sort"
        :options="listSortOptions"
        @update:model-value="
          change({
            lists_default_sort: $event as Preferences['lists_default_sort'],
          })
        "
      />
    </SettingsRow>
    <SettingsRow
      label="Count Plan to Watch in Statistics"
      hint="Adds Plan to Watch to totals, genre and score charts. Watch time only counts watched episodes."
    >
      <SettingsSwitch
        :model-value="prefs.stats_include_plan"
        label="Count Plan to Watch in Statistics"
        :disabled="!loaded"
        @update:model-value="change({ stats_include_plan: $event })"
      />
    </SettingsRow>
  </SettingsCard>
</template>

<style scoped>
.names {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
}
.saved {
  color: var(--ui-good-text);
  font-size: 12.5px;
}
.settings-section h2 {
  margin: 0 0 8px;
  padding-left: 12px;
  border-left: 3px solid var(--ui-accent);
  font-size: 1rem;
  color: var(--ui-heading);
}
.section-hint {
  color: var(--ui-dim);
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 14px;
}
.saved {
  color: var(--ui-good);
  margin-left: 8px;
  font-weight: 700;
}
.error {
  color: var(--ui-error);
  font-size: 0.82rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 14px 0;
  font-size: 0.82rem;
  color: var(--ui-text-soft);
}
.field small {
  color: var(--ui-faint);
}
.settings-section :deep(.toggle-button) {
  margin: 12px 0;
}
</style>
