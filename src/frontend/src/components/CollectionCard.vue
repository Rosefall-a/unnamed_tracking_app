<script setup lang="ts">
import { computed } from "vue";
import type { Game } from "../types/game";

const props = defineProps<{
  name: string;
  games: Game[];
  isSmart?: boolean;
}>();

const emit = defineEmits<{
  open: [name: string];
  delete: [];
}>();

const covers = computed(() =>
  props.games.slice(0, 4).map((g) => g.coverImageUrl),
);
const emptySlots = computed(() => Math.max(0, 4 - covers.value.length));

// nesting is a pure naming convention, "Parent/Child", not a separate
// data model, since collections have no backend row to hang real
// parent/child structure off in the first place
const slashIndex = computed(() => props.name.indexOf("/"));
const parentLabel = computed(() =>
  slashIndex.value === -1 ? null : props.name.slice(0, slashIndex.value),
);
const displayName = computed(() =>
  slashIndex.value === -1 ? props.name : props.name.slice(slashIndex.value + 1),
);
</script>

<template>
  <article class="collection-card-wrap">
    <button
      type="button"
      class="collection-open"
      :aria-label="`Open collection ${name}`"
      @click="emit('open', name)"
    >
      <div class="collection-card">
        <div class="cover">
          <div class="cover-grid">
            <div
              v-for="(cover, i) in covers"
              :key="i"
              class="cover-cell"
              :style="{ backgroundImage: `url(${cover})` }"
            ></div>
            <div
              v-for="i in emptySlots"
              :key="`empty-${i}`"
              class="cover-cell empty"
            ></div>
          </div>
          <span
            v-if="isSmart"
            class="smart-badge"
            title="Auto-updates based on a rule"
            >⚡ Auto</span
          >
        </div>
      </div>

      <div class="card-info">
        <span v-if="parentLabel" class="parent-eyebrow"
          >{{ parentLabel }} ›</span
        >
        <h3 class="title">{{ displayName }}</h3>
        <div class="meta-row">
          <span class="status"
            >{{ games.length }} game{{ games.length === 1 ? "" : "s" }}</span
          >
        </div>
      </div>
    </button>
    <button
      v-if="isSmart"
      type="button"
      class="smart-delete"
      :aria-label="`Delete smart collection ${name}`"
      title="Delete this smart collection"
      @click="emit('delete')"
    >
      ✕
    </button>
  </article>
</template>

<style scoped>
.collection-card-wrap {
  position: relative;
  width: 200px;
  min-width: 0;
}
.collection-open {
  display: block;
  width: 100%;
  padding: 0;
  border: 0;
  border-radius: var(--ui-radius-card);
  background: transparent;
  color: var(--ui-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.collection-card {
  position: relative;
  width: 100%;
  border-radius: var(--ui-radius-card);
  transition:
    transform 0.32s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.32s cubic-bezier(0.22, 1, 0.36, 1);
}
@media (hover: hover) {
  .collection-open:hover .collection-card {
    transform: translateY(-2px);
    box-shadow: var(--ui-elevation);
  }
}
.smart-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
  background: rgba(20, 20, 20, 0.75);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(214, 138, 52, 0.5);
  color: #d68a34;
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 999px;
}
.smart-delete {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: rgba(20, 20, 20, 0.75);
  backdrop-filter: blur(4px);
  color: #fff;
  font-size: 16px;
  cursor: pointer;
  opacity: 1;
  transition: opacity 0.15s ease;
}
@media (hover: hover) and (pointer: fine) {
  .smart-delete {
    opacity: 0;
  }
  .collection-card-wrap:hover .smart-delete,
  .collection-card-wrap:focus-within .smart-delete {
    opacity: 1;
  }
}
.smart-delete:hover {
  color: #fca5a5;
}
@media (max-width: 760px) {
  .smart-delete {
    opacity: 1;
  }
}
.cover {
  position: relative;
  width: 100%;
  /* matches GameCard's 2:3 (Steam-vertical) ratio so collection cards stay
     uniform with regular game cards */
  aspect-ratio: 2 / 3;
  border-radius: var(--ui-radius-card);
  overflow: hidden;
  background: var(--ui-surface);
}
.cover-grid {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 2px;
}
.cover-cell {
  background-size: cover;
  background-position: center;
  background-color: var(--ui-surface-2);
}
.cover-cell.empty {
  background-color: var(--ui-surface);
}
.card-info {
  padding: 10px 2px 0;
}
.parent-eyebrow {
  display: block;
  color: var(--ui-dim);
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 2px;
}
.title {
  margin: 0 0 2px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ui-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta-row {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--ui-dim);
}
</style>
