<script setup lang="ts">
// The Games counterpart of ListCard.vue, ported as it is: same 2x2 poster
// collage, badges, hover actions and info block, so a collection reads as the
// same kind of thing as a Media list. The only addition is the "Parent/Child"
// nesting label, since collections nest by name.
import { computed } from "vue";
import type { Game } from "../types/game";
import { blurOnLeave } from "../utils/blurOnLeave";

const props = defineProps<{
  name: string;
  games: Game[];
  isSmart?: boolean;
  // kept by the app (Favorites): can't be edited or deleted
  isSystem?: boolean;
  description?: string | null;
  pinned?: boolean;
  // the page is in "My order" with nothing filtered: show the move controls
  reorderable?: boolean;
  canMoveEarlier?: boolean;
  canMoveLater?: boolean;
  dragOver?: boolean;
}>();

const emit = defineEmits<{
  open: [name: string];
  delete: [name: string];
  edit: [name: string];
  pin: [name: string];
  move: [name: string, direction: -1 | 1];
  dragstart: [name: string];
  dragover: [name: string];
  drop: [name: string];
  dragend: [];
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
    :class="{ 'drop-target': dragOver }"
    :draggable="reorderable"
    @click="emit('open', name)"
    @dragstart="emit('dragstart', name)"
    @dragover.prevent="emit('dragover', name)"
    @drop.prevent="emit('drop', name)"
    @dragend="emit('dragend')"
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
          >{{ isSystem ? "Auto" : "Smart" }}</span
        >
        <span v-if="pinned" class="pin-badge" title="Pinned">
          <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
            <path
              d="M9 3h6l-1 6 3 3v2h-4v6l-1 1-1-1v-6H7v-2l3-3z"
              fill="currentColor"
            />
          </svg>
        </span>
        <div class="card-actions">
          <button
            type="button"
            :title="pinned ? 'Unpin this collection' : 'Pin this collection'"
            :class="{ on: pinned }"
            @click.stop="emit('pin', name)"
          >
            <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
              <path
                d="M9 3h6l-1 6 3 3v2h-4v6l-1 1-1-1v-6H7v-2l3-3z"
                fill="currentColor"
              />
            </svg>
          </button>
          <template v-if="reorderable">
            <button
              v-if="canMoveEarlier"
              type="button"
              title="Move earlier"
              @click.stop="emit('move', name, -1)"
            >
              &#9664;
            </button>
            <button
              v-if="canMoveLater"
              type="button"
              title="Move later"
              @click.stop="emit('move', name, 1)"
            >
              &#9654;
            </button>
          </template>
          <template v-if="!isSystem">
            <button
              type="button"
              title="Edit this collection"
              @click.stop="emit('edit', name)"
            >
              ✎
            </button>
            <button
              type="button"
              title="Delete this collection"
              @click.stop="emit('delete', name)"
            >
              ✕
            </button>
          </template>
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
        <span v-if="description" class="desc" :title="description">{{
          description
        }}</span>
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
.card-actions button:hover,
.card-actions button.on {
  color: #d68a34;
}
.pin-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(20, 20, 20, 0.8);
  backdrop-filter: blur(4px);
  color: #d68a34;
}
.collection-card-wrap[draggable="true"] {
  cursor: grab;
}
.collection-card-wrap.drop-target .collection-card {
  outline: 2px dashed #d68a34;
  outline-offset: 3px;
}
.card-actions button[title^="Delete"]:hover {
  color: #e57373;
}
.desc {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #666;
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
