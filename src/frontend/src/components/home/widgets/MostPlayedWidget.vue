<script setup lang="ts">
// Hours played in total, and the games you have put the most time into, as a
// bar each: Steam's "recent activity" idea, for the whole library.
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { homeData, titlesByKind } from "../../../home/data";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const SAMPLE = [
  ["Hollow Keep", 412],
  ["Starfall Run", 268],
  ["Tidewater", 141],
  ["Neon Ledger", 96],
  ["Ashen Road", 52],
] as const;

const covers = computed(
  () => new Map(titlesByKind.value.game.map((t) => [t.id, t])),
);

const rows = computed(() => {
  const limit = Number(props.settings.count) || 5;
  if (props.sample)
    return SAMPLE.slice(0, limit).map(([title, hours]) => ({
      id: title,
      title,
      hours,
      art: null as string | null,
      to: "",
    }));
  return (homeData.stats.value?.most_played ?? [])
    .filter((g) => g.playtime_seconds > 0)
    .slice(0, limit)
    .map((g) => ({
      id: g.id,
      title: g.title,
      hours: g.playtime_seconds / 3600,
      art: covers.value.get(g.id)?.art ?? null,
      to: `/games/${g.id}`,
    }));
});
const top = computed(() => Math.max(1, ...rows.value.map((r) => r.hours)));
const total = computed(() =>
  props.sample
    ? 1860
    : Math.round((homeData.stats.value?.total_playtime_seconds ?? 0) / 3600),
);
const fmt = (h: number) => (h >= 10 ? Math.round(h) : Math.round(h * 10) / 10);
</script>

<template>
  <WidgetFrame title="Time played" surface :sample="sample">
    <div v-if="rows.length" class="wrap">
      <div v-if="settings.showTotal !== false" class="total">
        <strong>{{ total.toLocaleString() }}</strong>
        <span>hours in total</span>
      </div>
      <ul class="list">
        <li v-for="r in rows" :key="r.id">
          <component
            :is="sample ? 'div' : 'router-link'"
            :to="sample ? undefined : r.to"
            class="row"
          >
            <span class="cover">
              <img v-if="r.art" :src="r.art" alt="" loading="lazy" />
              <span v-else>{{ r.title.charAt(0) }}</span>
            </span>
            <span class="words">
              <span class="line">
                <strong>{{ r.title }}</strong>
                <em>{{ fmt(r.hours) }} h</em>
              </span>
              <span class="bar"
                ><span :style="{ width: `${(r.hours / top) * 100}%` }"></span
              ></span>
            </span>
          </component>
        </li>
      </ul>
    </div>
    <div v-else class="none">
      <strong>{{ loading ? "Loading" : "No play time yet" }}</strong>
      <span v-if="!loading"
        >Hours come from a synced Steam or PlayStation library.</span
      >
    </div>
  </WidgetFrame>
</template>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.total {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.total strong {
  font-size: 1.9rem;
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.total span {
  color: var(--ui-dim);
  font-size: 0.84rem;
}
.list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 3px 4px;
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  text-decoration: none;
}
a.row:hover {
  background: var(--ui-surface-2);
}
.cover {
  flex: none;
  display: grid;
  place-items: center;
  width: 30px;
  height: 42px;
  overflow: hidden;
  border-radius: 5px;
  background: var(--ui-surface-3);
  color: var(--ui-dim);
  font-weight: 800;
}
.cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.words {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.line {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.84rem;
}
em {
  flex: none;
  color: var(--ui-dim);
  font-size: 0.76rem;
  font-style: normal;
  font-variant-numeric: tabular-nums;
}
.bar {
  display: block;
  height: 5px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--ui-surface-3);
}
.bar span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--ui-accent);
}
.none {
  display: grid;
  place-content: center;
  gap: 4px;
  height: 100%;
  text-align: center;
  color: var(--ui-dim);
  font-size: 0.84rem;
}
.none strong {
  color: var(--ui-text);
  white-space: normal;
}
</style>
