<script setup lang="ts">
// One card for anything shown as a 2x2 poster collage: a game collection or a
// Media list. The page decides what the covers, the count and the wording are;
// every event carries back the `id` it was given, so a collection (keyed by
// name) and a list (keyed by id) use it the same way.
import { computed } from "vue";
import { blurOnLeave } from "../utils/blurOnLeave";

const props = defineProps<{
  id: string;
  name: string;
  covers: (string | null | undefined)[];
  count: number;
  // "game" or "title", for the count line
  countNoun: string;
  // "collection" or "list", for the button tooltips
  noun: string;
  isSmart?: boolean;
  // kept by the app (Favorites): can't be edited or deleted
  isSystem?: boolean;
  description?: string | null;
  pinned?: boolean;
  // collections nest by naming: "Parent/Child" shows the parent above the name
  nestByName?: boolean;
  // the page is in "My order" with nothing filtered: show the move controls
  reorderable?: boolean;
  canMoveEarlier?: boolean;
  canMoveLater?: boolean;
  dragOver?: boolean;
}>();

const emit = defineEmits<{
  open: [id: string];
  delete: [id: string];
  edit: [id: string];
  pin: [id: string];
  move: [id: string, direction: -1 | 1];
  dragstart: [id: string];
  dragover: [id: string];
  drop: [id: string];
  dragend: [];
}>();

const shownCovers = computed(() => props.covers.slice(0, 4));
const emptySlots = computed(() => Math.max(0, 4 - shownCovers.value.length));

// nesting is a pure naming convention, "Parent/Child", not a separate data
// model: collections have no backend row to hang real structure off
const slashIndex = computed(() =>
  props.nestByName ? props.name.indexOf("/") : -1,
);
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
    @click="emit('open', id)"
    @dragstart="emit('dragstart', id)"
    @dragover.prevent="emit('dragover', id)"
    @drop.prevent="emit('drop', id)"
    @dragend="emit('dragend')"
    @mouseleave="blurOnLeave"
  >
    <div class="collection-card">
      <div class="cover">
        <div class="cover-grid">
          <div
            v-for="(cover, i) in shownCovers"
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
            :title="pinned ? `Unpin this ${noun}` : `Pin this ${noun}`"
            :class="{ on: pinned }"
            @click.stop="emit('pin', id)"
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
              @click.stop="emit('move', id, -1)"
            >
              &#9664;
            </button>
            <button
              v-if="canMoveLater"
              type="button"
              title="Move later"
              @click.stop="emit('move', id, 1)"
            >
              &#9654;
            </button>
          </template>
          <template v-if="!isSystem">
            <button
              type="button"
              :title="`Edit this ${noun}`"
              @click.stop="emit('edit', id)"
            >
              ✎
            </button>
            <button
              type="button"
              :title="`Delete this ${noun}`"
              @click.stop="emit('delete', id)"
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
          >{{ count }} {{ countNoun }}{{ count === 1 ? "" : "s" }}</span
        >
        <span v-if="description" class="desc" :title="description">{{
          description
        }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped src="../styles/shared/collectionTile.css"></style>
