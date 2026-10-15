<script setup lang="ts">
// How your library splits up: by genre or tag, platform, status, kind, rating or
// decade, as bars sized against the biggest. Counts are real titles.
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { KIND_LABEL, titlesOf } from "../../../home/data";
import type { HomeTitle } from "../../../home/data";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const GROUP_LABEL: Record<string, string> = {
  active: "In progress",
  queue: "Waiting",
  wishlist: "Wishlist",
  done: "Finished",
  dropped: "Dropped",
};

const BY: Record<string, { title: string; keys: (t: HomeTitle) => string[] }> =
  {
    genre: { title: "Top genres", keys: (t) => t.genres },
    platform: {
      title: "Platforms",
      keys: (t) => (t.platform ? [t.platform] : []),
    },
    status: {
      title: "By status",
      keys: (t) => [GROUP_LABEL[t.group] ?? t.group],
    },
    kind: { title: "By kind", keys: (t) => [KIND_LABEL[t.kind]] },
    rating: {
      title: "By rating",
      keys: (t) =>
        t.rating === null
          ? ["Not rated"]
          : [`${Math.floor(t.rating)} to ${Math.floor(t.rating) + 1}`],
    },
    maker: {
      title: "Top developers and studios",
      keys: (t) => t.makers,
    },
    decade: {
      title: "By decade",
      keys: (t) =>
        t.release
          ? [`${Math.floor(new Date(t.release).getFullYear() / 10) * 10}s`]
          : [],
    },
  };

const by = computed(() => BY[String(props.settings.by)] ?? BY.genre);

const SAMPLE = [
  ["Action", 42],
  ["RPG", 31],
  ["Adventure", 26],
  ["Indie", 18],
  ["Strategy", 11],
  ["Horror", 7],
] as const;

const rows = computed(() => {
  const limit = Number(props.settings.count) || 8;
  if (props.sample)
    return SAMPLE.slice(0, limit).map(([label, n]) => ({ label, n }));
  const counts = new Map<string, number>();
  for (const t of titlesOf(props.settings.kinds))
    for (const key of by.value.keys(t))
      counts.set(key, (counts.get(key) ?? 0) + 1);
  return [...counts.entries()]
    .map(([label, n]) => ({ label, n }))
    .sort((a, b) => b.n - a.n || a.label.localeCompare(b.label))
    .slice(0, limit);
});
const top = computed(() => Math.max(1, ...rows.value.map((r) => r.n)));
</script>

<template>
  <WidgetFrame :title="by.title" surface :sample="sample">
    <ul v-if="rows.length" class="bars">
      <li v-for="r in rows" :key="r.label">
        <span class="label">{{ r.label }}</span>
        <span class="track"
          ><span class="fill" :style="{ width: `${(r.n / top) * 100}%` }"></span
        ></span>
        <span class="n">{{ r.n }}</span>
      </li>
    </ul>
    <div v-else class="none">
      {{
        loading
          ? "Loading"
          : "Nothing to count yet. Try a different breakdown or include more kinds."
      }}
    </div>
  </WidgetFrame>
</template>

<style scoped>
.bars {
  display: flex;
  flex-direction: column;
  gap: 9px;
  margin: 0;
  padding: 0;
  list-style: none;
}
li {
  display: grid;
  grid-template-columns: minmax(70px, 28%) 1fr auto;
  align-items: center;
  gap: 10px;
  font-size: 0.82rem;
}
.label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ui-text);
}
.track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--ui-surface-3);
}
.fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--ui-accent);
}
.n {
  min-width: 2ch;
  color: var(--ui-dim);
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.none {
  display: grid;
  place-content: center;
  height: 100%;
  color: var(--ui-dim);
  font-size: 0.84rem;
  text-align: center;
}
</style>
