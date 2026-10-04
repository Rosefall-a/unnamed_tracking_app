<script setup lang="ts">
// The Games counterpart of ListCard.vue: same 2x2 poster-collage tile, badge,
// hover actions and info block, so a collection reads as the same kind of
// thing as a Media list. Pin, move and edit exist on lists only (they need
// stored data collections don't have), so the hover actions here are just
// delete, and only on smart collections.
import { computed } from "vue";
import type { Game } from "../types/game";
import { blurOnLeave } from "../utils/blurOnLeave";

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
  <div
    class="collection-card-wrap"
    role="button"
    tabindex="0"
    @click="emit('open', name)"
    @keydown.enter.self="emit('open', name)"
    @keydown.space.self.prevent="emit('open', name)"
    @mouseleave="blurOnLeave"
  >
    <div class="collection-card">
      <div class="cover">
        <div class="cover-grid">
          <div
            v-for="(cover, i) in covers"
            :key="i"
            class="cover-cell"
            :style="cover ? { backgroundImage: `url(${cover})` } : {}"
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
          title="Fills itself from a filter"
          >Smart</span
        >
        <div v-if="isSmart" class="card-actions">
          <button
            type="button"
            title="Delete this smart collection"
            @click.stop="emit('delete')"
          >
            ✕
          </button>
        </div>
      </div>
    </div>

    <div class="card-info">
      <span v-if="parentLabel" class="parent-eyebrow">{{ parentLabel }} ›</span>
      <h3 class="title">{{ displayName }}</h3>
      <div class="meta-row">
        <span class="status"
          >{{ games.length }} game{{ games.length === 1 ? "" : "s" }}</span
        >
      </div>
    </div>
  </div>
</template>

<style scoped>
.collection-card-wrap {
  width: 200px;
  cursor: pointer;
}
.collection-card {
  position: relative;
  width: 100%;
  border-radius: 10px;
  transition:
    transform 0.32s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.32s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform;
}
.collection-card-wrap:hover .collection-card {
  transform: scale(1.07) translateY(-4px);
  box-shadow: 0 24px 56px rgba(0, 0, 0, 0.5);
}
.card-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 6px;
  opacity: 0;
  transition: opacity 0.15s ease;
}
.collection-card-wrap:hover .card-actions,
.collection-card-wrap:focus-within .card-actions {
  opacity: 1;
}
/* no hover on touch screens: keep the actions reachable */
@media (hover: none) {
  .card-actions {
    opacity: 1;
  }
}
.card-actions button {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: none;
  background: rgba(20, 20, 20, 0.78);
  backdrop-filter: blur(4px);
  color: #ccc;
  font-size: 11px;
  cursor: pointer;
}
.card-actions button:hover {
  color: #e57373;
}
.cover {
  position: relative;
  width: 100%;
  aspect-ratio: 2 / 3;
  border-radius: 10px;
  overflow: hidden;
  background: #1a1a1a;
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
  background-color: #1c1c1c;
}
.cover-cell.empty {
  background-color: #161616;
}
.smart-badge {
  position: absolute;
  left: 8px;
  bottom: 8px;
  z-index: 2;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(20, 20, 20, 0.8);
  backdrop-filter: blur(4px);
  color: #d68a34;
}
.card-info {
  padding: 10px 2px 0;
}
.parent-eyebrow {
  display: block;
  color: #666;
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 2px;
}
.title {
  margin: 0 0 2px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta-row {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #9c9c9c;
}
</style>
