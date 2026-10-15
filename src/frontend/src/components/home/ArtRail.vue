<script setup lang="ts">
// A row of artwork cards that takes its card size from the height it is given,
// so a taller widget shows bigger art. It scrolls sideways when there are more
// cards than fit. With nothing to show it draws the row anyway, as empty tiles
// with one line saying what belongs here, so a widget never looks broken.
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { CHROME_KEY } from "../../home/chrome";
import ArtCard from "./ArtCard.vue";

export interface RailItem {
  key: string;
  title: string;
  art: string | null;
  subtitle?: string;
  progress?: number | null;
  to?: string | null;
  tag?: string | null;
  tagKind?: string | null;
  badge?: string | null;
}

const props = withDefaults(
  defineProps<{
    items: RailItem[];
    shape?: "poster" | "wide" | "square";
    loading?: boolean;
    sample?: boolean;
    emptyTitle?: string;
    emptyHint?: string;
    emptyTo?: string;
    emptyAction?: string;
  }>(),
  { shape: "poster", emptyTitle: "Nothing here yet" },
);

const RATIO = { poster: 2 / 3, wide: 16 / 9, square: 1 } as const;
// the tallest a card gets, so a tall widget gets more room, not giant art
const CAP = {
  poster: { small: 170, medium: 210, large: 260 },
  wide: { small: 120, medium: 150, large: 190 },
  square: { small: 90, medium: 120, large: 150 },
} as const;
const ratio = computed(() => RATIO[props.shape]);
const chrome = inject(CHROME_KEY, null);
const cap = computed(
  () => `${CAP[props.shape][chrome?.value.cardSize ?? "medium"]}px`,
);
const cardText = computed(() => chrome?.value.cardText ?? "always");
// the kind label: on every card, on none, or only when the row mixes kinds
const showTags = computed(() => {
  const mode = chrome?.value.cardTag ?? "auto";
  if (mode !== "auto") return mode === "always";
  return new Set(props.items.map((i) => i.tagKind).filter(Boolean)).size > 1;
});

const row = ref<HTMLElement | null>(null);
const canBack = ref(false);
const canForward = ref(false);
function measure() {
  const el = row.value;
  if (!el) return;
  canBack.value = el.scrollLeft > 4;
  canForward.value = el.scrollLeft < el.scrollWidth - el.clientWidth - 4;
}
function nudge(direction: 1 | -1) {
  const el = row.value;
  if (el)
    el.scrollBy({
      left: direction * el.clientWidth * 0.85,
      behavior: "smooth",
    });
}
let observer: ResizeObserver | null = null;
onMounted(() => {
  if (row.value) {
    observer = new ResizeObserver(measure);
    observer.observe(row.value);
  }
  measure();
});
onBeforeUnmount(() => observer?.disconnect());
watch(
  () => props.items.length,
  () => requestAnimationFrame(measure),
);

const empty = computed(() => !props.items.length);
</script>

<template>
  <div class="rail-wrap" :style="{ '--ratio': ratio, '--cap': cap }">
    <div
      ref="row"
      class="rail"
      :class="{ ghosts: empty }"
      @scroll.passive="measure"
    >
      <template v-if="!empty">
        <div v-for="it in items" :key="it.key" class="cell">
          <ArtCard
            :title="it.title"
            :art="it.art"
            :subtitle="it.subtitle"
            :progress="it.progress ?? null"
            :to="it.to"
            :tag="showTags ? it.tag : null"
            :tag-kind="it.tagKind"
            :badge="it.badge"
            :text="cardText"
            :sample="sample"
          />
        </div>
      </template>
      <template v-else>
        <div v-for="n in 8" :key="n" class="cell">
          <div
            class="ghost"
            :class="{ pulse: loading }"
            :style="{ '--n': n }"
          ></div>
        </div>
      </template>
    </div>
    <div v-if="empty && !loading" class="message">
      <strong>{{ emptyTitle }}</strong>
      <span v-if="emptyHint">{{ emptyHint }}</span>
      <router-link v-if="emptyTo && emptyAction" :to="emptyTo" class="action">
        {{ emptyAction }}
      </router-link>
    </div>
    <button
      v-if="canBack"
      type="button"
      class="nudge back"
      aria-label="Scroll back"
      @click="nudge(-1)"
    >
      &#8249;
    </button>
    <button
      v-if="canForward"
      type="button"
      class="nudge forward"
      aria-label="Scroll forward"
      @click="nudge(1)"
    >
      &#8250;
    </button>
  </div>
</template>

<style scoped>
.rail-wrap {
  position: relative;
  height: 100%;
}
.rail {
  display: grid;
  grid-auto-flow: column;
  --card-h: min(100cqh, var(--cap));
  grid-auto-columns: calc(var(--card-h) * var(--ratio));
  grid-template-rows: var(--card-h);
  gap: 12px;
  height: 100%;
  align-content: start;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
  scroll-snap-type: x proximity;
}
.rail::-webkit-scrollbar {
  display: none;
}
.cell {
  min-width: 0;
  scroll-snap-align: start;
}
.ghost {
  height: 100%;
  border: 1px dashed var(--ui-border);
  border-radius: var(--ui-radius-row);
  background: color-mix(
    in srgb,
    var(--ui-accent) calc(2% + var(--n) * 0.6%),
    var(--ui-surface)
  );
  opacity: calc(1 - var(--n) * 0.09);
}
.pulse {
  animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
  50% {
    opacity: 0.45;
  }
}
.message {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 12px;
  text-align: center;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--ui-bg) 88%, transparent) 25%,
    color-mix(in srgb, var(--ui-bg) 20%, transparent)
  );
  color: var(--ui-dim);
  font-size: 0.84rem;
}
.message strong {
  color: var(--ui-text);
  font-size: 0.95rem;
}
.action {
  margin-top: 8px;
  padding: 7px 16px;
  border-radius: var(--ui-radius-control);
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  font-weight: 700;
  text-decoration: none;
}
.action:hover {
  filter: brightness(1.08);
}
.nudge {
  position: absolute;
  top: 50%;
  width: 32px;
  height: 32px;
  margin-top: -16px;
  border: 1px solid var(--ui-border-strong);
  border-radius: 50%;
  background: color-mix(in srgb, var(--ui-bg) 86%, transparent);
  color: var(--ui-text);
  font-size: 1.2rem;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s;
}
.rail-wrap:hover .nudge,
.nudge:focus-visible {
  opacity: 1;
}
.back {
  left: 4px;
}
.forward {
  right: 4px;
}
@media (prefers-reduced-motion: reduce) {
  .pulse {
    animation: none;
  }
}
</style>
