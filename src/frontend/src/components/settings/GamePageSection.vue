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
    error.value = e instanceof Error ? e.message : "Could not load settings.";
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
    error.value = e instanceof Error ? e.message : "Could not save.";
    settings.value = previous;
  }
}
</script>

<template>
  <p v-if="error" class="st-error">{{ error }}</p>
  <p v-if="savedNote" class="saved">{{ savedNote }}</p>
  <PageSettingsEditor
    v-if="loaded"
    layout="cards"
    :model-value="settings"
    @update:model-value="change($event as PageSettings)"
  />
</template>

<style scoped>
.saved {
  margin: 0;
  color: var(--ui-good-text);
  font-size: 12.5px;
}
</style>
