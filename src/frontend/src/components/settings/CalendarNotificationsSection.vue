<script setup lang="ts">
// Calendar and notification preferences. These are stored on the server
// (not in this browser), so they follow you between devices, and each
// change saves as soon as it is made.
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

const viewOptions = [
  { value: "month", label: "Month" },
  { value: "agenda", label: "Agenda" },
];
const retentionOptions = [
  { value: "7", label: "7 days" },
  { value: "14", label: "14 days" },
  { value: "30", label: "30 days" },
  { value: "90", label: "90 days" },
  { value: "0", label: "Never" },
];
const weekOptions = [
  { value: "0", label: "Sunday" },
  { value: "1", label: "Monday" },
];
</script>

<template>
  <section class="settings-section">
    <h2>Calendar and Notifications</h2>
    <p class="section-hint">
      Saved on the server, so they follow you between browsers.
      <span v-if="savedNote" class="saved">{{ savedNote }}</span>
    </p>
    <p v-if="error" class="error">{{ error }}</p>

    <h3>Calendar</h3>
    <ToggleButton
      :model-value="prefs.calendar_game_releases"
      label="Game releases"
      :disabled="!loaded"
      @update:model-value="change({ calendar_game_releases: $event })"
    >
      <strong>Game releases</strong>: show upcoming release dates for games on
      your Wishlist or Backlog
    </ToggleButton>
    <ToggleButton
      :model-value="prefs.calendar_game_history"
      label="Games history"
      :disabled="!loaded"
      @update:model-value="change({ calendar_game_history: $event })"
    >
      <strong>Games history</strong>: show the day you finished a game and the
      days you unlocked achievements
    </ToggleButton>

    <ToggleButton
      :model-value="prefs.calendar_show_estimated"
      label="Estimated episodes"
      :disabled="!loaded"
      @update:model-value="change({ calendar_show_estimated: $event })"
    >
      <strong>Estimated episodes</strong>: show later episodes projected from
      the show's usual schedule (drawn dashed). Only the next episode of a show
      is a confirmed date.
    </ToggleButton>
    <ToggleButton
      :model-value="prefs.calendar_hide_games"
      label="Hide all Games layers"
      :disabled="!loaded"
      @update:model-value="change({ calendar_hide_games: $event })"
    >
      <strong>Hide all Games layers</strong>: keep games off the calendar even
      when the two options above are on
    </ToggleButton>

    <div class="field">
      <span>Opens in</span>
      <SegmentedControl
        :model-value="prefs.calendar_default_view"
        :options="viewOptions"
        @update:model-value="
          change({
            calendar_default_view:
              $event as Preferences['calendar_default_view'],
          })
        "
      />
    </div>
    <div class="field">
      <span>Week starts on</span>
      <SegmentedControl
        :model-value="String(prefs.calendar_week_start)"
        :options="weekOptions"
        @update:model-value="
          change({
            calendar_week_start: Number(
              $event,
            ) as Preferences['calendar_week_start'],
          })
        "
      />
    </div>

    <h3>Notifications</h3>
    <p class="section-hint">
      Built from exact air times and release dates, never from estimates. They
      show under Notifications in the sidebar.
    </p>
    <div class="field">
      <span>Clear notifications after</span>
      <SegmentedControl
        :model-value="String(prefs.notification_retention_days)"
        :options="retentionOptions"
        @update:model-value="
          change({
            notification_retention_days: Number(
              $event,
            ) as Preferences['notification_retention_days'],
          })
        "
      />
    </div>
    <ToggleButton
      :model-value="prefs.notify_episode_aired"
      label="Episode aired"
      :disabled="!loaded"
      @update:model-value="change({ notify_episode_aired: $event })"
    >
      <strong>Episode aired</strong>: a new episode of something you are
      watching, planning to watch or have on hold
    </ToggleButton>
    <ToggleButton
      :model-value="prefs.notify_season_started"
      label="Season started airing"
      :disabled="!loaded"
      @update:model-value="change({ notify_season_started: $event })"
    >
      <strong>Season started airing</strong>: the first episode of a season
      aired
    </ToggleButton>
    <ToggleButton
      :model-value="prefs.notify_sequel_announced"
      label="New season listed"
      :disabled="!loaded"
      @update:model-value="change({ notify_sequel_announced: $event })"
    >
      <strong>New season listed</strong>: a sequel appears for an anime you
      completed
    </ToggleButton>
    <ToggleButton
      :model-value="prefs.notify_movie_released"
      label="Movie released"
      :disabled="!loaded"
      @update:model-value="change({ notify_movie_released: $event })"
    >
      <strong>Movie released</strong>: a movie you were waiting on has come out
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
.settings-section h3 {
  margin: 22px 0 8px;
  font-size: 0.86rem;
  color: #ddd;
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
.settings-section :deep(.toggle-button) {
  margin: 12px 0;
}
</style>
