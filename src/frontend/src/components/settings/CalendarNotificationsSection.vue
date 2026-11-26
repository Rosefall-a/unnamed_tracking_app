<script setup lang="ts">
// Calendar and notification preferences. These are stored on the server
// (not in this browser), so they follow you between devices, and each
// change saves as soon as it is made.
import { ref, computed, onMounted } from "vue";
import SettingsCard from "./SettingsCard.vue";
import SettingsRow from "./SettingsRow.vue";
import SettingsSwitch from "./SettingsSwitch.vue";
import MultiSegment from "./MultiSegment.vue";
import SegmentedControl from "./SegmentedControl.vue";
import {
  DEFAULT_PREFERENCES,
  fetchPreferences,
  queuePreferences,
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

type NotifyStatus = Preferences["notify_statuses"][number];
type NotifyType = Preferences["notify_media_types"][number];
// switch one member of a set-valued preference on or off
function setMember<T extends string>(list: T[], value: T, on: boolean): T[] {
  return on
    ? [...list.filter((v) => v !== value), value]
    : list.filter((v) => v !== value);
}
const NOTIFY_STATUS_ROWS: { key: NotifyStatus; label: string; hint: string }[] =
  [
    {
      key: "watching",
      label: "Watching",
      hint: "titles you are in the middle of",
    },
    {
      key: "plan",
      label: "Plan to Watch",
      hint: "titles you have not started",
    },
    { key: "hold", label: "On Hold", hint: "titles you put aside" },
  ];
const NOTIFY_TYPE_ROWS: { key: NotifyType; label: string }[] = [
  { key: "anime", label: "Anime" },
  { key: "tv", label: "TV shows" },
  { key: "movie", label: "Movies" },
];

const viewOptions = [
  { value: "month", label: "Month" },
  { value: "week", label: "Week" },
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
  { value: "0", label: "Sun" },
  { value: "1", label: "Mon" },
  { value: "2", label: "Tue" },
  { value: "3", label: "Wed" },
  { value: "4", label: "Thu" },
  { value: "5", label: "Fri" },
  { value: "6", label: "Sat" },
];

// options that only do something while another one is on are greyed out, with the reason
const hiddenReason = "Game layers are hidden from the calendar above.";
const episodicOn = computed(
  () =>
    prefs.value.notify_media_types.includes("anime") ||
    prefs.value.notify_media_types.includes("tv"),
);
const episodicReason = "Turn on Anime or TV shows under Kinds above.";
const animeOn = computed(() =>
  prefs.value.notify_media_types.includes("anime"),
);
const animeReason = "Turn on Anime under Kinds above.";
// a film is never "watching", so it needs Plan to Watch or On Hold as well
const moviesOn = computed(
  () =>
    prefs.value.notify_media_types.includes("movie") &&
    (prefs.value.notify_statuses.includes("plan") ||
      prefs.value.notify_statuses.includes("hold")),
);
const moviesReason = "Turn on Movies, and Plan to Watch or On Hold, above.";

const props = withDefaults(
  defineProps<{ part?: "calendar" | "notifications" }>(),
  { part: "calendar" },
);
</script>

<template>
  <p v-if="error" class="st-error">{{ error }}</p>
  <p v-if="savedNote" class="saved">{{ savedNote }}</p>
  <template v-if="props.part === 'calendar'">
    <SettingsCard title="What the calendar shows">
      <SettingsRow
        label="Game releases"
        :hint="
          prefs.calendar_hide_games && hiddenReason
            ? hiddenReason
            : 'The release date of every game, past and upcoming'
        "
      >
        <SettingsSwitch
          :model-value="prefs.calendar_game_releases"
          label="Game releases"
          :disabled="!loaded || prefs.calendar_hide_games"
          @update:model-value="change({ calendar_game_releases: $event })"
        />
      </SettingsRow>
      <SettingsRow
        label="Games history"
        :hint="
          prefs.calendar_hide_games && hiddenReason
            ? hiddenReason
            : 'The day you finished a game and the days you unlocked achievements'
        "
      >
        <SettingsSwitch
          :model-value="prefs.calendar_game_history"
          label="Games history"
          :disabled="!loaded || prefs.calendar_hide_games"
          @update:model-value="change({ calendar_game_history: $event })"
        />
      </SettingsRow>
      <SettingsRow
        label="Estimated episodes"
        hint="Later episodes projected from the usual schedule, drawn dashed. Only the next episode is a confirmed date."
      >
        <SettingsSwitch
          :model-value="prefs.calendar_show_estimated"
          label="Estimated episodes"
          :disabled="!loaded"
          @update:model-value="change({ calendar_show_estimated: $event })"
        />
      </SettingsRow>
      <SettingsRow
        label="Hide all Games layers"
        hint="Keeps games off the calendar even when the two above are on"
      >
        <SettingsSwitch
          :model-value="prefs.calendar_hide_games"
          label="Hide all Games layers"
          :disabled="!loaded"
          @update:model-value="change({ calendar_hide_games: $event })"
        />
      </SettingsRow>
    </SettingsCard>
    <SettingsCard title="Episodes for titles that are">
      <SettingsRow
        v-for="row in NOTIFY_STATUS_ROWS"
        :key="row.key"
        :label="row.label"
        :hint="row.hint"
      >
        <SettingsSwitch
          :model-value="prefs.calendar_airing_statuses.includes(row.key)"
          :label="row.label"
          :disabled="!loaded"
          @update:model-value="
            change({
              calendar_airing_statuses: setMember(
                prefs.calendar_airing_statuses,
                row.key,
                $event,
              ),
            })
          "
        />
      </SettingsRow>
    </SettingsCard>
    <SettingsCard title="Layout">
      <SettingsRow label="Opens in">
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
      </SettingsRow>
      <SettingsRow label="Week starts on">
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
      </SettingsRow>
    </SettingsCard>
  </template>

  <template v-else>
    <SettingsCard
      title="Which titles"
      description="Episode alerts come only from these. Completed and Dropped never send them; new season and sequel notices follow their own switches."
    >
      <SettingsRow label="Kinds">
        <MultiSegment
          :model-value="prefs.notify_media_types"
          :options="
            NOTIFY_TYPE_ROWS.map((r) => ({ value: r.key, label: r.label }))
          "
          :disabled="!loaded"
          @update:model-value="
            change({
              notify_media_types: $event as typeof prefs.notify_media_types,
            })
          "
        />
      </SettingsRow>
      <SettingsRow
        v-for="row in NOTIFY_STATUS_ROWS"
        :key="row.key"
        :label="row.label"
        :hint="row.hint"
      >
        <SettingsSwitch
          :model-value="prefs.notify_statuses.includes(row.key)"
          :label="row.label"
          :disabled="!loaded"
          @update:model-value="
            change({
              notify_statuses: setMember(
                prefs.notify_statuses,
                row.key,
                $event,
              ),
            })
          "
        />
      </SettingsRow>
    </SettingsCard>
    <SettingsCard
      title="What to tell me about"
      description="Built from exact air times and release dates, never estimates. They show in the bell at the top of every page."
    >
      <SettingsRow
        label="Episode aired"
        :hint="
          !episodicOn && episodicReason
            ? episodicReason
            : 'A new episode of something you are watching, planning to watch or have on hold'
        "
      >
        <SettingsSwitch
          :model-value="prefs.notify_episode_aired"
          label="Episode aired"
          :disabled="!loaded || !episodicOn"
          @update:model-value="change({ notify_episode_aired: $event })"
        />
      </SettingsRow>
      <SettingsRow
        label="Season started airing"
        :hint="
          !episodicOn && episodicReason
            ? episodicReason
            : 'The first episode of a season aired'
        "
      >
        <SettingsSwitch
          :model-value="prefs.notify_season_started"
          label="Season started airing"
          :disabled="!loaded || !episodicOn"
          @update:model-value="change({ notify_season_started: $event })"
        />
      </SettingsRow>
      <SettingsRow
        label="New season listed"
        :hint="
          !animeOn && animeReason
            ? animeReason
            : 'A sequel appears for an anime you completed. Needs the New season check task.'
        "
      >
        <SettingsSwitch
          :model-value="prefs.notify_sequel_announced"
          label="New season listed"
          :disabled="!loaded || !animeOn"
          @update:model-value="change({ notify_sequel_announced: $event })"
        />
      </SettingsRow>
      <SettingsRow
        label="New movie or special listed"
        :hint="
          !animeOn && animeReason
            ? animeReason
            : 'A film, OVA or special appears for an anime you completed. Needs the New season check task.'
        "
      >
        <SettingsSwitch
          :model-value="prefs.notify_extras_announced"
          label="New movie or special listed"
          :disabled="!loaded || !animeOn"
          @update:model-value="change({ notify_extras_announced: $event })"
        />
      </SettingsRow>
      <SettingsRow
        label="Movie released"
        :hint="
          !moviesOn && moviesReason
            ? moviesReason
            : 'A movie you were waiting on has come out'
        "
      >
        <SettingsSwitch
          :model-value="prefs.notify_movie_released"
          label="Movie released"
          :disabled="!loaded || !moviesOn"
          @update:model-value="change({ notify_movie_released: $event })"
        />
      </SettingsRow>
      <SettingsRow
        label="Achievement milestone"
        hint="100th unlock, 10th perfect game, first under 1%"
      >
        <SettingsSwitch
          :model-value="prefs.notify_achievement_milestone"
          label="Achievement milestone"
          :disabled="!loaded"
          @update:model-value="change({ notify_achievement_milestone: $event })"
        />
      </SettingsRow>
      <SettingsRow
        label="Game hits 100%"
        hint="A pop-up the moment the last achievement syncs, and a line here"
      >
        <SettingsSwitch
          :model-value="prefs.notify_game_complete"
          label="Game hits 100%"
          :disabled="!loaded"
          @update:model-value="change({ notify_game_complete: $event })"
        />
      </SettingsRow>
    </SettingsCard>
    <SettingsCard title="Clean up">
      <SettingsRow label="Clear read notifications after">
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
      </SettingsRow>
    </SettingsCard>
  </template>
</template>

<style scoped>
.saved {
  margin: 0;
  color: var(--ui-good-text);
  font-size: 12.5px;
}
</style>
