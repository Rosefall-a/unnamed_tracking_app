<script setup lang="ts">
// What every game's page shows by default: which tabs, which buttons, and the
// tab it opens on. A game can override any of it from its own Edit dialog.
// Saved on the server as it is changed.
import { ref, onMounted } from "vue";
import PageSettingsEditor from "../PageSettingsEditor.vue";
import {
  DEFAULT_PREFERENCES,
  fetchPreferences,
  queuePreferences,
} from "../../services/preferences";
import { preferences as sharedPreferences } from "../../state/preferences";
import { resolvePage } from "../../utils/gamePage";
import type { PageSettings } from "../../utils/gamePage";

const settings = ref<PageSettings>(
  resolvePage(DEFAULT_PREFERENCES.game_page, null),
);
const loaded = ref(false);
const error = ref<string | null>(null);
const savedNote = ref("");

onMounted(async () => {
  try {
    settings.value = resolvePage((await fetchPreferences()).game_page, null);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load settings.";
  } finally {
    loaded.value = true;
  }
});

async function change(next: PageSettings) {
  const previous = settings.value;
  settings.value = next;
  error.value = null;
  try {
    const { prefs, latest } = await queuePreferences({ game_page: next });
    if (latest) {
      settings.value = resolvePage(prefs.game_page, null);
      sharedPreferences.value = prefs;
    }
    savedNote.value = "Saved";
    setTimeout(() => (savedNote.value = ""), 1500);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save.";
    settings.value = previous;
  }
}
</script>

<template>
  <section class="settings-section">
    <h2>Game Page</h2>
    <p class="section-hint">
      Choose what a game's page shows, for every game. Hide the tabs you never
      use, or set them to Auto so they appear once a game has something in them.
      A single game can override any of this from its Edit dialog, on the Page
      tab.
      <span v-if="savedNote" class="saved">{{ savedNote }}</span>
    </p>
    <p v-if="error" class="error">{{ error }}</p>
    <PageSettingsEditor
      v-if="loaded"
      :model-value="settings"
      @update:model-value="change($event as PageSettings)"
    />
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
  color: #999;
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 20px;
}
.saved {
  margin-left: 8px;
  color: #d68a34;
  font-weight: 700;
}
.error {
  color: #fca5a5;
  font-size: 0.85rem;
}
</style>
