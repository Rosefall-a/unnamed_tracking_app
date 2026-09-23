<script setup lang="ts">
// Defaults for the Movies, TV and Anime libraries, Lists and Statistics.
// Saved on the server as they are changed.
import { ref, onMounted } from "vue";
import SegmentedControl from "./SegmentedControl.vue";
import ToggleButton from "./ToggleButton.vue";
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
    const { prefs: saved, latest } = await queuePreferences(changes);
    if (latest) {
      prefs.value = saved;
      sharedPreferences.value = saved;
    }
    savedNote.value = "Saved";
    setTimeout(() => (savedNote.value = ""), 1500);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save.";
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
      e instanceof Error ? e.message : "Failed to look up titles.";
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
      <span>Anime names</span>
      <SegmentedControl
        :model-value="prefs.title_language"
        :options="titleLanguageOptions"
        @update:model-value="
          change({
            title_language: $event as Preferences['title_language'],
          })
        "
      />
      <small
        >Which spelling is the main name, for example ERASED or Boku dake ga
        Inai Machi. The other spellings are shown under the name on the anime
        page. If a spelling is not known for a title, the next best is used.
        Anime added before this existed need their titles looked up once.</small
      >
      <button
        type="button"
        class="ui-btn ui-btn-secondary ui-btn-sm"
        :disabled="fillingTitles"
        @click="lookUpTitles"
      >
        {{ fillingTitles ? "Looking up…" : "Look up titles for my anime" }}
      </button>
      <small v-if="titlesNote">{{ titlesNote }}</small>
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
