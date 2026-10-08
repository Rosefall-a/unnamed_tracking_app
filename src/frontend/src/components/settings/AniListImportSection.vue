<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import SegmentedControl from "./SegmentedControl.vue";
import ToggleButton from "./ToggleButton.vue";
import {
  DEFAULT_PREFERENCES,
  fetchPreferences,
  queuePreferences,
} from "../../services/preferences";
import type { Preferences } from "../../services/preferences";

const prefs = ref<Preferences>({ ...DEFAULT_PREFERENCES });
const loaded = ref(false);
const error = ref<string | null>(null);
const saved = ref(false);
const importing = ref(false);
const importMessage = ref<string | null>(null);

// a one-time import of the saved username, on top of the scheduled one
async function importNow() {
  const username = prefs.value.anilist_import_username.trim();
  if (!username) return;
  importing.value = true;
  importMessage.value = null;
  error.value = null;
  try {
    const response = await fetch("/api/anime/import/anilist", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username,
        update_existing: prefs.value.anilist_import_update_existing,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail ?? "AniList import failed.");
    importMessage.value = `Fetched ${data.fetched}, created ${data.created}, updated ${data.updated}, skipped ${data.skipped}.`;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "AniList import failed.";
  } finally {
    importing.value = false;
  }
}

const cadenceOptions = [
  { value: "60", label: "Hourly" },
  { value: "360", label: "Every 6 hours" },
  { value: "720", label: "Twice daily" },
  { value: "1440", label: "Daily" },
  { value: "10080", label: "Weekly" },
];
const customCadence = ref(false);
const customHours = computed({
  get: () => Math.round(prefs.value.anilist_import_interval_minutes / 60),
  set: (hours: number) => {
    prefs.value.anilist_import_interval_minutes =
      Math.min(720, Math.max(1, Math.round(hours))) * 60;
  },
});

onMounted(async () => {
  try {
    prefs.value = await fetchPreferences();
    customCadence.value = !cadenceOptions.some(
      (o) => Number(o.value) === prefs.value.anilist_import_interval_minutes,
    );
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load settings.";
  } finally {
    loaded.value = true;
  }
});

async function change(changes: Partial<Preferences>) {
  prefs.value = { ...prefs.value, ...changes };
  error.value = null;
  try {
    const { prefs: savedPrefs } = await queuePreferences(changes);
    prefs.value = savedPrefs;
    saved.value = true;
    setTimeout(() => (saved.value = false), 1500);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save.";
  }
}

async function setCadence(value: string) {
  customCadence.value = false;
  await change({ anilist_import_interval_minutes: Number(value) });
}

async function setCustomCadence(hours: number) {
  customCadence.value = true;
  const minutes = Math.min(30 * 24 * 60, Math.max(60, Math.round(hours * 60)));
  await change({ anilist_import_interval_minutes: minutes });
}
</script>

<template>
  <section class="settings-section">
    <h2>AniList Import</h2>
    <p class="section-hint">
      Automatically import your public AniList anime list into this library. The
      import only reads AniList and never changes it.
      <span v-if="saved" class="saved">Saved</span>
    </p>
    <p v-if="error" class="error">{{ error }}</p>
    <ToggleButton
      :model-value="prefs.anilist_import_enabled"
      label="Automatic AniList import"
      :disabled="!loaded"
      @update:model-value="change({ anilist_import_enabled: $event })"
    >
      <strong>Automatic import</strong>: periodically sync the public list below
      into your anime library
    </ToggleButton>
    <div class="field">
      <label for="anilist-username">AniList username</label>
      <input
        id="anilist-username"
        :value="prefs.anilist_import_username"
        maxlength="100"
        placeholder="Your AniList username"
        :disabled="!loaded"
        @change="
          change({
            anilist_import_username: ($event.target as HTMLInputElement).value,
          })
        "
      />
    </div>
    <div class="field">
      <span>Import frequency</span>
      <SegmentedControl
        v-if="!customCadence"
        :model-value="String(prefs.anilist_import_interval_minutes)"
        :options="cadenceOptions"
        @update:model-value="setCadence"
      />
      <button
        v-else
        type="button"
        class="custom-button"
        @click="customCadence = false"
      >
        Custom: every {{ customHours }} hour{{ customHours === 1 ? "" : "s" }}
      </button>
    </div>
    <div class="field custom-field">
      <label for="anilist-hours">Or use a custom interval (hours)</label>
      <input
        id="anilist-hours"
        type="number"
        min="1"
        max="720"
        :value="customHours"
        :disabled="!loaded"
        @change="
          setCustomCadence(Number(($event.target as HTMLInputElement).value))
        "
      />
    </div>
    <ToggleButton
      :model-value="prefs.anilist_import_update_existing"
      label="Update existing titles"
      :disabled="!loaded"
      @update:model-value="change({ anilist_import_update_existing: $event })"
    >
      <strong>Update existing titles</strong>: apply AniList list changes to
      titles already in the library
    </ToggleButton>
    <div class="import-now">
      <button
        type="button"
        class="ui-btn ui-btn-secondary"
        :disabled="
          !loaded || importing || !prefs.anilist_import_username.trim()
        "
        @click="importNow"
      >
        {{ importing ? "Importing…" : "Import now" }}
      </button>
      <span v-if="importMessage" class="saved">{{ importMessage }}</span>
    </div>
    <p class="section-hint">
      The scheduler runs in the app background once a minute. Imports are
      bounded so a large multi-user deployment cannot monopolize the worker.
    </p>
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
.field input {
  width: min(100%, 420px);
  box-sizing: border-box;
  padding: 9px 11px;
  border: 1px solid #3a3a3a;
  border-radius: 7px;
  background: #111;
  color: #eee;
}
.custom-field {
  max-width: 420px;
}
.custom-button {
  align-self: flex-start;
  padding: 8px 12px;
  border: 1px solid #444;
  border-radius: 7px;
  background: #222;
  color: #ddd;
  cursor: pointer;
}
.import-now {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 14px 0;
}
.settings-section :deep(.toggle-button) {
  margin: 12px 0;
}
</style>
