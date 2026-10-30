<script setup lang="ts">
// Every show and anime you are partway through, with the episode you are up to and
// how far through each one is: a quick list to pick up where you left off.
import { computed } from "vue";
import WidgetFrame from "../WidgetFrame.vue";
import { ago, titlesByKind } from "../../../home/data";
import { sampleTitles } from "../../../home/samples";
import { asKinds } from "../../../home/rail";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const rows = computed(() => {
  const count = Number(props.settings.count) || 8;
  if (props.sample)
    return sampleTitles(count, ["tv", "anime"]).map((t) => ({
      ...t,
      touchedAt: Date.now() - 86_400_000,
    }));
  const kinds = asKinds(props.settings.kinds);
  const wanted = kinds.length ? kinds : (["tv", "anime"] as const);
  return wanted
    .filter((k) => k !== "game" && k !== "movie")
    .flatMap((k) => titlesByKind.value[k])
    .filter((t) => t.group === "active")
    .sort((a, b) => b.touchedAt - a.touchedAt)
    .slice(0, count);
});
</script>

<template>
  <WidgetFrame title="Next episodes" :sample="sample">
    <ul v-if="rows.length" class="list">
      <li v-for="t in rows" :key="t.key">
        <component
          :is="sample ? 'div' : 'router-link'"
          :to="sample ? undefined : t.to"
          class="row"
        >
          <span class="thumb">
            <img v-if="t.art" :src="t.art" alt="" loading="lazy" />
            <span v-else>{{ t.title.charAt(0) }}</span>
          </span>
          <span class="words">
            <strong>{{ t.title }}</strong>
            <small>
              Up next {{ t.subtitle
              }}<template v-if="t.touchedAt">
                · watched {{ ago(t.touchedAt) }}</template
              >
            </small>
            <span
              v-if="settings.showProgress !== false && t.progress !== null"
              class="bar"
              ><span
                :style="{ width: `${Math.round(t.progress * 100)}%` }"
              ></span
            ></span>
          </span>
          <span v-if="t.progress !== null" class="pct"
            >{{ Math.round(t.progress * 100) }}%</span
          >
        </component>
      </li>
    </ul>
    <div v-else class="none">
      <strong>{{ loading ? "Loading" : "Nothing in progress" }}</strong>
      <span v-if="!loading">Shows and anime you are watching show here.</span>
    </div>
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
  gap: 12px;
  padding: 8px 12px 8px 8px;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface);
  color: var(--ui-text);
  text-decoration: none;
}
a.row:hover {
  border-color: var(--ui-accent-line);
}
.thumb {
  flex: none;
  display: grid;
  place-items: center;
  width: 44px;
  height: 62px;
  overflow: hidden;
  border-radius: 7px;
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
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.92rem;
}
small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ui-dim);
  font-size: 0.78rem;
}
.bar {
  display: block;
  height: 4px;
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
.pct {
  flex: none;
  color: var(--ui-dim);
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
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
