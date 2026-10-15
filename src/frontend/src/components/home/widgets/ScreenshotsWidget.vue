<script setup lang="ts">
// A wall of your latest screenshots from across every game, like Steam's
// screenshot showcase: the newest one large, the rest around it, filling the space
// the widget has in whole tiles that never run past its edges. Each one opens its
// game.
import { computed, onBeforeUnmount, ref, watch } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { homeData } from "../../../home/data";
import { shuffle } from "../../../home/select";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

interface Shot {
  id: string;
  url: string | null;
  game: string;
  to: string;
  n: number;
}

const all = computed<Shot[]>(() => {
  if (props.sample)
    return Array.from({ length: 12 }, (_, i) => ({
      id: String(i),
      url: null,
      game: ["Hollow Keep", "Starfall Run", "Tidewater", "Neon Ledger"][i % 4],
      to: "",
      n: i,
    }));
  const list = [...(homeData.screenshots.value ?? [])];
  const ordered =
    props.settings.order === "random"
      ? shuffle(list)
      : list.sort(
          (a, b) => (b.taken_at ?? b.created_at) - (a.taken_at ?? a.created_at),
        );
  return ordered.map((s, i) => ({
    id: s.id,
    url: s.url,
    game: s.game_title ?? "",
    to: s.game_id ? `/games/${s.game_id}` : "",
    n: i,
  }));
});

// ---- how many tiles fit ----
const wallEl = ref<HTMLElement | null>(null);
const cols = ref(4);
const rows = ref(2);
function measure() {
  const el = wallEl.value;
  if (!el) return;
  cols.value = Math.max(2, Math.min(8, Math.round(el.clientWidth / 150)));
  rows.value = Math.max(1, Math.min(5, Math.round(el.clientHeight / 96)));
}
let observer: ResizeObserver | null = null;
watch(wallEl, (el) => {
  observer?.disconnect();
  observer = null;
  if (!el) return;
  observer = new ResizeObserver(measure);
  observer.observe(el);
  measure();
});
onBeforeUnmount(() => observer?.disconnect());

// the newest is a 2 by 2 tile when there is room for one
const featured = computed(() => cols.value >= 3 && rows.value >= 2);
const capacity = computed(
  () => cols.value * rows.value - (featured.value ? 3 : 0),
);
const shown = computed(() => {
  const limit = Number(props.settings.count) || 12;
  return all.value.slice(0, Math.min(limit, capacity.value));
});
</script>

<template>
  <WidgetFrame title="Screenshots" :sample="sample">
    <div
      v-if="shown.length"
      ref="wallEl"
      class="wall"
      :style="{ '--cols': cols, '--rows': rows }"
    >
      <component
        :is="sample || !s.to ? 'div' : 'router-link'"
        v-for="(s, i) in shown"
        :key="s.id"
        :to="sample || !s.to ? undefined : s.to"
        class="shot"
        :class="{ big: featured && i === 0 }"
        :style="{ '--n': s.n }"
      >
        <img v-if="s.url" :src="s.url" alt="" loading="lazy" />
        <span v-if="s.game" class="game">{{ s.game }}</span>
      </component>
    </div>
    <div v-else class="none">
      <strong>{{ loading ? "Loading" : "No screenshots yet" }}</strong>
      <span v-if="!loading"
        >Upload screenshots on a game's page and they show up here.</span
      >
    </div>
  </WidgetFrame>
</template>

<style scoped>
.wall {
  display: grid;
  grid-template-columns: repeat(var(--cols), minmax(0, 1fr));
  grid-template-rows: repeat(var(--rows), minmax(0, 1fr));
  grid-auto-flow: dense;
  gap: 8px;
  height: 100%;
}
.shot {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-row);
  background: color-mix(
    in srgb,
    var(--ui-accent) calc(8% + var(--n) * 2%),
    var(--ui-surface-2)
  );
  color: var(--ui-on-art);
  text-decoration: none;
}
.shot.big {
  grid-column: span 2;
  grid-row: span 2;
}
a.shot:hover {
  border-color: var(--ui-accent-line);
}
.shot img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}
a.shot:hover img {
  transform: scale(1.05);
}
.game {
  position: absolute;
  inset: auto 0 0 0;
  padding: 16px 9px 6px;
  overflow: hidden;
  background: linear-gradient(
    to top,
    color-mix(in srgb, var(--ui-scrim-base) 80%, transparent),
    transparent
  );
  font-size: 0.72rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
  opacity: 0;
  transition: opacity 0.15s;
}
.big .game {
  font-size: 0.82rem;
}
.shot:hover .game {
  opacity: 1;
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
}
@media (prefers-reduced-motion: reduce) {
  .shot img {
    transition: none;
  }
}
</style>
