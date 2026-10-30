<script setup lang="ts">
// The next episode of each show you are watching, soonest first, with a live
// countdown. Only dates a provider has confirmed are shown: the calendar page
// also lists weekly guesses for later episodes, and a countdown to a guess would
// be a made-up number.
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import ArtRail from "../ArtRail.vue";
import type { RailItem } from "../ArtRail.vue";
import { allTitles, homeData, routeFor } from "../../../home/data";
import { airPhrase, countdown, useNow } from "../../../home/clock";
import { sampleCalendar } from "../../../home/samples";
import type { CalendarEntry } from "../../../services/mediaExtras";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();
const now = useNow();

const byKey = computed(() => new Map(allTitles.value.map((t) => [t.key, t])));

const entries = computed<CalendarEntry[]>(() => {
  const count = Number(props.settings.count) || 8;
  if (props.sample) return sampleCalendar(count);
  const limit =
    Date.now() / 1000 + (Number(props.settings.days) || 14) * 86_400;
  const kinds = Array.isArray(props.settings.kinds)
    ? (props.settings.kinds as string[])
    : [];
  return (homeData.calendar.value ?? [])
    .filter((e) => {
      if (e.isProjected || e.airAt > limit || e.mediaType === "game")
        return false;
      if (kinds.length && !kinds.includes(e.mediaType)) return false;
      if (props.settings.onlyWatching !== false)
        return (
          byKey.value.get(`${e.mediaType}:${e.mediaId}`)?.group === "active"
        );
      return true;
    })
    .sort((a, b) => a.airAt - b.airAt)
    .slice(0, count);
});

function when(e: CalendarEntry): string {
  return new Date(e.airAt * 1000).toLocaleString(undefined, {
    weekday: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}
function episode(e: CalendarEntry): string {
  if (e.kind === "release") return "Premiere";
  return e.nextEpisodeNumber ? `Episode ${e.nextEpisodeNumber}` : "New episode";
}
const clock = (e: CalendarEntry) =>
  countdown(e.airAt, now.value, props.settings.showSeconds === true);
const showClock = computed(() => props.settings.showCountdown !== false);

const asPosters = computed(() => props.variant === "posters");
const cards = computed<RailItem[]>(() =>
  entries.value.map((e) => ({
    key: `${e.mediaType}:${e.mediaId}:${e.airAt}`,
    title: e.title,
    art: e.posterUrl,
    subtitle: `${episode(e)} · ${when(e)}`,
    badge: showClock.value ? airPhrase(clock(e)) : null,
    to: routeFor(e.mediaType, e.mediaId),
  })),
);
</script>

<template>
  <WidgetFrame
    title="Airing soon"
    :sample="sample"
    :link="{ to: '/calendar', label: 'Calendar' }"
  >
    <ul v-if="!asPosters && entries.length" class="list">
      <li v-for="e in entries" :key="`${e.mediaType}:${e.mediaId}:${e.airAt}`">
        <component
          :is="sample ? 'div' : 'router-link'"
          :to="sample ? undefined : routeFor(e.mediaType, e.mediaId)"
          class="row"
        >
          <span class="thumb">
            <img v-if="e.posterUrl" :src="e.posterUrl" alt="" loading="lazy" />
            <span v-else>{{ e.title.charAt(0) }}</span>
          </span>
          <span class="words">
            <strong>{{ e.title }}</strong>
            <small>{{ episode(e) }} · {{ when(e) }}</small>
          </span>
          <span v-if="showClock" class="clock">{{ clock(e) }}</span>
        </component>
      </li>
    </ul>
    <div v-else-if="!asPosters" class="empty">
      <strong>{{ loading ? "Loading" : "Nothing airing soon" }}</strong>
      <span v-if="!loading"
        >Episodes with a confirmed air date for shows you are watching show
        here.</span
      >
      <router-link v-if="!loading" to="/calendar">Open calendar</router-link>
    </div>
    <ArtRail
      v-else
      :items="cards"
      shape="poster"
      :loading="loading"
      :sample="sample"
      empty-title="Nothing airing soon"
      empty-hint="Episodes with a confirmed air date for shows you are watching show here."
      empty-to="/calendar"
      empty-action="Open calendar"
    />
  </WidgetFrame>
</template>

<style scoped>
.list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  height: 100%;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
  scrollbar-width: thin;
}
.row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 14px 8px 8px;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface);
  color: var(--ui-text);
  text-decoration: none;
  transition: border-color 0.15s;
}
a.row:hover {
  border-color: var(--ui-accent-line);
}
.thumb {
  flex: none;
  display: grid;
  place-items: center;
  width: 52px;
  height: 74px;
  overflow: hidden;
  border-radius: 8px;
  background: var(--ui-surface-3);
  color: var(--ui-dim);
  font-size: 1.2rem;
  font-weight: 800;
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.words {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 1rem;
}
small {
  color: var(--ui-dim);
  font-size: 0.84rem;
}
.clock {
  flex: none;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--ui-accent-soft);
  color: var(--ui-accent);
  font-size: 0.95rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.empty {
  display: grid;
  place-content: center;
  gap: 6px;
  height: 100%;
  border: 1px dashed var(--ui-border);
  border-radius: var(--ui-radius-card);
  text-align: center;
  color: var(--ui-dim);
  font-size: 0.86rem;
}
.empty strong {
  color: var(--ui-text);
}
.empty a {
  color: var(--ui-accent);
  font-weight: 700;
  text-decoration: none;
}
</style>
