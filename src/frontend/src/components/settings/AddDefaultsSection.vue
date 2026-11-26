<script setup lang="ts">
// Library › Adding: the status a new game, film, show or anime starts with when
// you press Add, so it does not have to be changed by hand every time. Saved to
// your account like the rest of your preferences.
import { ref } from "vue";
import SettingsCard from "./SettingsCard.vue";
import SettingsRow from "./SettingsRow.vue";
import { queuePreferences } from "../../services/preferences";
import type { Preferences } from "../../services/preferences";
import { preferences } from "../../state/preferences";
import { STATUS_BUCKETS } from "../../utils/mediaStatus";

type AddKey =
  "add_status_game" | "add_status_movie" | "add_status_tv" | "add_status_anime";

const GAME_STATUSES: { value: string; label: string }[] = [
  { value: "wishlist", label: "Wishlist" },
  { value: "backlog", label: "Backlog" },
  { value: "playing", label: "Playing" },
  { value: "on hold", label: "On hold" },
  { value: "played", label: "Played" },
  { value: "beaten", label: "Beaten" },
  { value: "mastered", label: "Mastered" },
  { value: "dropped", label: "Dropped" },
];
const MEDIA_STATUSES = STATUS_BUCKETS.map((b) => ({
  value: b.key,
  label: b.label,
}));

const ROWS: {
  key: AddKey;
  label: string;
  options: { value: string; label: string }[];
}[] = [
  { key: "add_status_game", label: "Games", options: GAME_STATUSES },
  { key: "add_status_movie", label: "Movies", options: MEDIA_STATUSES },
  { key: "add_status_tv", label: "TV shows", options: MEDIA_STATUSES },
  { key: "add_status_anime", label: "Anime", options: MEDIA_STATUSES },
];

const error = ref<string | null>(null);
const saved = ref("");
// only the newest save's answer is applied, so quick changes never undo each other
let seq = 0;
async function change(key: AddKey, value: string) {
  const mine = ++seq;
  const before = preferences.value;
  preferences.value = { ...before, [key]: value } as Preferences;
  error.value = null;
  try {
    const { prefs } = await queuePreferences({ [key]: value });
    if (mine !== seq) return;
    preferences.value = { ...preferences.value, ...prefs };
    saved.value = "Saved";
    window.setTimeout(() => (saved.value = ""), 1500);
  } catch (e) {
    if (mine !== seq) return;
    preferences.value = before;
    error.value = e instanceof Error ? e.message : "Could not save.";
  }
}
</script>

<template>
  <SettingsCard
    title="Status when you add"
    description="What a new title starts as when you press Add to Library. You can still change it in the dialog before adding."
  >
    <template v-if="saved" #actions>
      <span class="st-muted">{{ saved }}</span>
    </template>
    <SettingsRow v-for="row in ROWS" :key="row.key" :label="row.label">
      <select
        class="st-select"
        :value="preferences[row.key]"
        :aria-label="`Status for new ${row.label.toLowerCase()}`"
        @change="change(row.key, ($event.target as HTMLSelectElement).value)"
      >
        <option v-for="o in row.options" :key="o.value" :value="o.value">
          {{ o.label }}
        </option>
      </select>
    </SettingsRow>
    <p v-if="error" class="st-error">{{ error }}</p>
  </SettingsCard>
</template>
