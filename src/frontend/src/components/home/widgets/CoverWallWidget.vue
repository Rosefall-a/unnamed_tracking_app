<script setup lang="ts">
// Covers laid out as a wall that fills the widget exactly: as many whole posters
// as fit, no scrolling. Pick what it shows the same way as a shelf.
import { computed, inject, onBeforeUnmount, ref, watch } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import ArtCard from "../ArtCard.vue";
import { CHROME_KEY } from "../../../home/chrome";
import { KIND_NOUN, titlesOf } from "../../../home/data";
import type { HomeTitle } from "../../../home/data";
import { asKinds } from "../../../home/rail";
import { sampleTitles } from "../../../home/samples";
import { narrow, sortTitles } from "../../../home/select";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();
const chrome = inject(CHROME_KEY, null);

const PICK: Record<string, (t: HomeTitle) => boolean> = {
  "recently-added": () => true,
  "recently-updated": () => true,
  backlog: (t) => t.group === "queue",
  wishlist: (t) => t.group === "wishlist",
  favorites: (t) => t.favorite,
  "highest-rated": (t) => t.rating !== null,
  finished: (t) => t.group === "done",
  everything: () => true,
};

const all = computed(() => {
  if (props.sample) return sampleTitles(60, asKinds(props.settings.kinds));
  const picked = narrow(
    titlesOf(props.settings.kinds).filter(
      PICK[String(props.settings.source)] ?? PICK["recently-added"],
    ),
    props.settings,
  );
  return sortTitles(
    picked,
    props.settings.sort,
    props.settings.source === "highest-rated" ? "rating" : "added",
  );
});

// ---- how many covers fit ----
const SIZE: Record<string, number> = { small: 92, medium: 124, large: 160 };
const wallEl = ref<HTMLElement | null>(null);
const cols = ref(6);
const rows = ref(2);
const GAP = 8;
function measure() {
  const el = wallEl.value;
  if (!el) return;
  // a cover is never allowed to be taller than the wall, so a short widget gets
  // more, smaller covers instead of one cut off at the bottom
  const tallest = Math.max(40, el.clientHeight / 1.5);
  const w = Math.min(SIZE[String(props.settings.tile)] ?? 124, tallest);
  cols.value = Math.max(1, Math.floor((el.clientWidth + GAP) / (w + GAP)));
  if ((el.clientWidth - GAP * (cols.value - 1)) / cols.value > tallest)
    cols.value = Math.ceil((el.clientWidth + GAP) / (tallest + GAP));
  // the covers take their height from their width, so rows follow from that
  const tileW = (el.clientWidth - GAP * (cols.value - 1)) / cols.value;
  const tileH = tileW * 1.5;
  rows.value = Math.max(1, Math.floor((el.clientHeight + GAP) / (tileH + GAP)));
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
watch(
  () => props.settings.tile,
  () => requestAnimationFrame(measure),
);
onBeforeUnmount(() => observer?.disconnect());

const shown = computed(() => all.value.slice(0, cols.value * rows.value));
const mixed = computed(() => new Set(shown.value.map((t) => t.kind)).size > 1);
const tagMode = computed(() => chrome?.value.cardTag ?? "auto");
const showTag = computed(
  () => tagMode.value === "always" || (tagMode.value === "auto" && mixed.value),
);
</script>

<template>
  <WidgetFrame title="Cover wall" :sample="sample">
    <div
      v-if="shown.length || loading"
      ref="wallEl"
      class="wall"
      :style="{ '--cols': cols }"
    >
      <div v-for="t in shown" :key="t.key" class="tile">
        <ArtCard
          :title="t.title"
          :art="t.art"
          :subtitle="t.subtitle"
          :to="t.to"
          :tag="showTag ? KIND_NOUN[t.kind] : null"
          :tag-kind="t.kind"
          :text="
            chrome?.cardText === 'always'
              ? 'hover'
              : (chrome?.cardText ?? 'hover')
          "
          :sample="sample"
        />
      </div>
    </div>
    <div v-else class="none">
      <strong>Nothing to show</strong>
      <span>Change what the wall shows in this widget's settings.</span>
    </div>
  </WidgetFrame>
</template>

<style scoped>
.wall {
  display: grid;
  grid-template-columns: repeat(var(--cols), minmax(0, 1fr));
  grid-auto-rows: min-content;
  align-content: start;
  gap: 8px;
  height: 100%;
  overflow: hidden;
}
.tile {
  aspect-ratio: 2 / 3;
  min-width: 0;
}
.none {
  display: grid;
  place-content: center;
  gap: 4px;
  height: 100%;
  border: 1px dashed var(--ui-border);
  border-radius: var(--ui-radius-card);
  text-align: center;
  color: var(--ui-dim);
  font-size: 0.84rem;
}
.none strong {
  color: var(--ui-text);
}
</style>
