<script setup lang="ts">
// The coming days laid out as a board: one column for each day that has
// something, with what airs or comes out in it. Episodes are only the ones with
// a confirmed air date; the calendar's weekly guesses for later episodes are
// left out.
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { allTitles, homeData, routeFor } from "../../../home/data";
import { sampleCalendar } from "../../../home/samples";
import type { CalendarEntry } from "../../../services/mediaExtras";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const byKey = computed(() => new Map(allTitles.value.map((t) => [t.key, t])));

const entries = computed<CalendarEntry[]>(() => {
  if (props.sample) return sampleCalendar(9);
  const now = Date.now() / 1000;
  const limit = now + (Number(props.settings.days) || 7) * 86_400;
  const include = Array.isArray(props.settings.include)
    ? (props.settings.include as string[])
    : [];
  return (homeData.calendar.value ?? []).filter((e) => {
    if (e.airAt < now - 3600 || e.airAt > limit) return false;
    if (e.mediaType === "game") return include.includes("games");
    if (e.kind === "release") return include.includes("premieres");
    if (!include.includes("episodes") || e.isProjected) return false;
    if (props.settings.onlyWatching !== false)
      return byKey.value.get(`${e.mediaType}:${e.mediaId}`)?.group === "active";
    return true;
  });
});

const days = computed(() => {
  const groups = new Map<
    string,
    { label: string; at: number; items: CalendarEntry[] }
  >();
  const today = new Date();
  const startToday = new Date(
    today.getFullYear(),
    today.getMonth(),
    today.getDate(),
  ).getTime();
  for (const e of [...entries.value].sort((a, b) => a.airAt - b.airAt)) {
    const d = new Date(e.airAt * 1000);
    const start = new Date(
      d.getFullYear(),
      d.getMonth(),
      d.getDate(),
    ).getTime();
    const key = String(start);
    if (!groups.has(key)) {
      const diff = Math.round((start - startToday) / 86_400_000);
      groups.set(key, {
        label:
          diff === 0
            ? "Today"
            : diff === 1
              ? "Tomorrow"
              : d.toLocaleDateString(undefined, { weekday: "long" }),
        at: start,
        items: [],
      });
    }
    groups.get(key)!.items.push(e);
  }
  return [...groups.values()];
});

function time(e: CalendarEntry): string {
  return new Date(e.airAt * 1000).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}
function what(e: CalendarEntry): string {
  if (e.mediaType === "game") return "Release";
  if (e.kind === "release") return "Premiere";
  return e.nextEpisodeNumber ? `Episode ${e.nextEpisodeNumber}` : "New episode";
}
const dateLabel = (at: number) =>
  new Date(at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
</script>

<template>
  <WidgetFrame
    title="Release schedule"
    :sample="sample"
    :link="{ to: '/calendar', label: 'Open the calendar' }"
  >
    <div v-if="days.length" class="board">
      <section v-for="d in days" :key="d.at" class="day">
        <header>
          <strong>{{ d.label }}</strong>
          <span>{{ dateLabel(d.at) }}</span>
        </header>
        <component
          :is="sample ? 'div' : 'router-link'"
          v-for="e in d.items"
          :key="`${e.mediaType}:${e.mediaId}:${e.airAt}`"
          :to="sample ? undefined : routeFor(e.mediaType, e.mediaId)"
          class="item"
        >
          <span class="thumb">
            <img v-if="e.posterUrl" :src="e.posterUrl" alt="" loading="lazy" />
            <span v-else>{{ e.title.charAt(0) }}</span>
          </span>
          <span class="words">
            <strong>{{ e.title }}</strong>
            <small>{{ what(e) }} · {{ time(e) }}</small>
          </span>
        </component>
      </section>
    </div>
    <div v-else class="empty">
      <strong>{{ loading ? "Loading" : "Nothing scheduled" }}</strong>
      <span v-if="!loading"
        >Confirmed episodes, premieres and game releases in the next few days
        show here. Look further ahead using the controls above.</span
      >
    </div>
  </WidgetFrame>
</template>

<style scoped>
.board {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(190px, 1fr);
  gap: 12px;
  height: 100%;
  overflow-x: auto;
  scrollbar-width: thin;
}
.day {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  overflow-y: auto;
  padding-right: 2px;
  scrollbar-width: thin;
}
.day header {
  position: sticky;
  top: 0;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 2px 2px 6px;
  border-bottom: 1px solid var(--ui-border-soft);
  background: var(--ui-bg);
}
.day header strong {
  font-size: 0.86rem;
}
.day header span {
  color: var(--ui-faint);
  font-size: 0.72rem;
}
.item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-row);
  background: var(--ui-surface);
  color: var(--ui-text);
  text-decoration: none;
}
a.item:hover {
  border-color: var(--ui-accent-line);
}
.thumb {
  flex: none;
  display: grid;
  place-items: center;
  width: 38px;
  height: 54px;
  overflow: hidden;
  border-radius: 6px;
  background: var(--ui-surface-3);
  color: var(--ui-dim);
  font-weight: 800;
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.words {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.words strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.86rem;
}
.words small {
  color: var(--ui-accent);
  font-size: 0.74rem;
  font-weight: 600;
}
.empty {
  display: grid;
  place-content: center;
  gap: 4px;
  height: 100%;
  border: 1px dashed var(--ui-border);
  border-radius: var(--ui-radius-card);
  padding: 10px;
  text-align: center;
  color: var(--ui-dim);
  font-size: 0.84rem;
}
.empty strong {
  color: var(--ui-text);
}
</style>
