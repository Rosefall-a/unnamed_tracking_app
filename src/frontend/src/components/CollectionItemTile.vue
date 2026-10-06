<script setup lang="ts">
// One game, movie, show or anime inside a collection or list: poster, name and
// a status pill. In reorder mode it is draggable and shows move arrows;
// otherwise a star (use as the cover) and a remove button show on hover.
defineProps<{
  title: string;
  posterUrl: string | null | undefined;
  statusLabel: string;
  statusClass: string;
  index: number;
  count: number;
  reorderMode: boolean;
  dragging: boolean;
  // this item is the cover: shown as a lit star on the button...
  starOn?: boolean;
  // ...or as a small star in the poster corner
  coverMark?: boolean;
  // tooltip of that corner star
  coverMarkTitle?: string;
  starTitle: string;
  removeTitle: string;
  canRemove: boolean;
}>();

const emit = defineEmits<{
  open: [];
  nudge: [delta: -1 | 1];
  cover: [];
  remove: [];
  dragstart: [event: DragEvent];
  dragover: [];
  dragend: [];
}>();
</script>

<template>
  <div
    class="item-card"
    :class="{ reordering: reorderMode, dragging }"
    :draggable="reorderMode"
    @click="emit('open')"
    @dragstart="emit('dragstart', $event)"
    @dragover.prevent="emit('dragover')"
    @dragend="emit('dragend')"
  >
    <div class="item-cover">
      <div
        class="item-poster"
        :style="posterUrl ? { backgroundImage: `url(${posterUrl})` } : {}"
      ></div>
      <span
        v-if="coverMark"
        class="cover-mark"
        :title="coverMarkTitle ?? 'Cover'"
        >★</span
      >
      <div v-if="reorderMode" class="reorder-arrows">
        <button
          type="button"
          :disabled="index === 0"
          title="Move earlier"
          @click.stop="emit('nudge', -1)"
        >
          ‹
        </button>
        <span class="reorder-pos">{{ index + 1 }}</span>
        <button
          type="button"
          :disabled="index === count - 1"
          title="Move later"
          @click.stop="emit('nudge', 1)"
        >
          ›
        </button>
      </div>
      <div v-else class="tile-actions">
        <button
          type="button"
          class="tile-btn star"
          :class="{ on: starOn }"
          :title="starTitle"
          @click.stop="emit('cover')"
        >
          ★
        </button>
        <button
          v-if="canRemove"
          type="button"
          class="tile-btn"
          :title="removeTitle"
          @click.stop="emit('remove')"
        >
          ✕
        </button>
      </div>
    </div>
    <div class="card-info">
      <h3 class="title">{{ title }}</h3>
      <span class="pill" :class="statusClass">{{ statusLabel }}</span>
    </div>
  </div>
</template>

<style scoped>
.item-card {
  cursor: pointer;
}

.item-card.reordering {
  cursor: grab;
}

.item-card.dragging {
  opacity: 0.4;
}

.item-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 2 / 3;
  border-radius: 10px;
  overflow: hidden;
  background: #1a1a1a;
  transition:
    transform 0.32s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.32s cubic-bezier(0.22, 1, 0.36, 1);
}

.item-card:hover .item-cover {
  transform: scale(1.07) translateY(-4px);
  box-shadow: 0 24px 56px rgba(0, 0, 0, 0.5);
}

.item-card.reordering:hover .item-cover {
  transform: none;
  box-shadow: none;
}

.item-poster {
  width: 100%;
  height: 100%;
  background-size: cover;
  background-repeat: no-repeat;
  background-position: center;
  background-color: #1c1c1c;
}

.tile-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: none;
  background: rgba(20, 20, 20, 0.75);
  backdrop-filter: blur(4px);
  color: #ccc;
  font-size: 11px;
  cursor: pointer;
}

.reorder-arrows {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.85));
}

.reorder-arrows button {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  font-size: 15px;
  cursor: pointer;
}

.reorder-arrows button:disabled {
  opacity: 0.3;
  cursor: default;
}

.reorder-pos {
  font-size: 12px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.card-info {
  padding: 10px 2px 0;
}

.title {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pill {
  display: inline-flex;
  align-items: center;
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  padding: 3px 9px;
  border-radius: 999px;
}

.pill.watching {
  background: rgba(214, 138, 52, 0.16);
  color: #d68a34;
}

.pill.completed {
  background: rgba(111, 191, 115, 0.16);
  color: #6fbf73;
}

.pill.hold {
  background: rgba(123, 167, 217, 0.16);
  color: #7ba7d9;
}

.pill.dropped {
  background: rgba(217, 111, 111, 0.16);
  color: #d96f6f;
}

.pill.plan {
  background: rgba(157, 140, 217, 0.16);
  color: #9d8cd9;
}
.cover-mark {
  position: absolute;
  left: 8px;
  top: 8px;
  z-index: 2;
  color: #d68a34;
  font-size: 14px;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.8);
}

.tile-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* the buttons appear on hover, except the star that is currently the cover,
   which stays lit so the cover is always visible */
.tile-btn {
  opacity: 0;
  transition: opacity 0.15s ease;
}

.item-card:hover .tile-btn,
.tile-btn.on {
  opacity: 1;
}

.tile-btn:hover {
  color: #e57373;
}

.tile-btn.star:hover,
.tile-btn.on {
  color: #d68a34;
}
</style>
