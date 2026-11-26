<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import SegmentedControl from "./SegmentedControl.vue";
import SettingsCard from "./SettingsCard.vue";
import SettingsRow from "./SettingsRow.vue";
import SettingsSwitch from "./SettingsSwitch.vue";
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
  { value: "720", label: "Every 12 hours" },
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
    error.value = e instanceof Error ? e.message : "Could not load settings.";
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
    error.value = e instanceof Error ? e.message : "Could not save.";
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
  <SettingsCard
    title="AniList"
    description="Reads your public AniList list into your anime library. AniList itself is never changed."
  >
    <template #actions>
      <span v-if="saved" class="saved">Saved</span>
    </template>
    <p v-if="error" class="st-error">{{ error }}</p>
    <SettingsRow label="AniList username">
      <input
        id="anilist-username"
        class="st-field name-field"
        aria-label="AniList username"
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
    </SettingsRow>
    <SettingsRow
      label="Import automatically"
      hint="On a schedule, in the background"
    >
      <div class="cadence">
        <SegmentedControl
          v-if="!customCadence"
          :model-value="String(prefs.anilist_import_interval_minutes)"
          :options="cadenceOptions"
          @update:model-value="setCadence"
        />
        <button
          v-else
          type="button"
          class="st-btn"
          @click="customCadence = false"
        >
          Custom: every {{ customHours }} hour{{ customHours === 1 ? "" : "s" }}
        </button>
        <SettingsSwitch
          :model-value="prefs.anilist_import_enabled"
          label="Import automatically"
          :disabled="!loaded"
          @update:model-value="change({ anilist_import_enabled: $event })"
        />
      </div>
    </SettingsRow>
    <SettingsRow label="Custom interval" hint="Hours between imports">
      <input
        id="anilist-hours"
        class="st-field hours-field"
        aria-label="Custom interval in hours"
        type="number"
        min="1"
        max="720"
        :value="customHours"
        :disabled="!loaded"
        @change="
          setCustomCadence(Number(($event.target as HTMLInputElement).value))
        "
      />
    </SettingsRow>
    <SettingsRow
      label="Update titles already in the library"
      hint="Apply AniList changes to anime you already have"
    >
      <SettingsSwitch
        :model-value="prefs.anilist_import_update_existing"
        label="Update titles already in the library"
        :disabled="!loaded"
        @update:model-value="change({ anilist_import_update_existing: $event })"
      />
    </SettingsRow>
    <div class="st-btns import-now">
      <button
        type="button"
        class="st-btn"
        :disabled="
          !loaded || importing || !prefs.anilist_import_username.trim()
        "
        @click="importNow"
      >
        {{ importing ? "Importing…" : "Import now" }}
      </button>
      <span v-if="importMessage" class="saved">{{ importMessage }}</span>
    </div>
  </SettingsCard>
</template>

<style scoped>
.saved {
  color: var(--ui-good-text);
  font-size: 12.5px;
}
.name-field {
  max-width: 260px;
}
.hours-field {
  width: 90px;
}
.cadence {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.import-now {
  align-items: center;
  margin-top: 6px;
}
</style>
