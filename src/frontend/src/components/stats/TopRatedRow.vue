<script setup lang="ts">
// The big row of top-rated poster cards from the library Stats tab: rank
// badge, poster, two-line title, score. A card opens that title.
import type { TopTitle } from "../../services/mediaStats";

defineProps<{ items: TopTitle[]; limit?: number }>();
defineEmits<{ open: [item: TopTitle] }>();
</script>

<template>
  <div class="toprated-row">
    <button
      v-for="(it, i) in items.slice(0, limit ?? 5)"
      :key="`${it.kind}-${it.id}`"
      type="button"
      class="toprated-card"
      @click="$emit('open', it)"
    >
      <span class="toprated-rank">#{{ i + 1 }}</span>
      <span
        class="toprated-art"
        :style="it.posterUrl ? { backgroundImage: `url(${it.posterUrl})` } : {}"
      >
        <span v-if="!it.posterUrl" class="toprated-initial">{{ it.title.slice(0, 1) }}</span>
      </span>
      <span class="toprated-title">{{ it.title }}</span>
      <span class="toprated-score">★ {{ it.score }}</span>
    </button>
  </div>
</template>

<style scoped>
.toprated-row {
  display: flex;
  gap: 14px;
  overflow-x: auto;
  padding-bottom: 4px;
}
.toprated-card {
  position: relative;
  flex-shrink: 0;
  width: 120px;
  display: block;
  padding: 0;
  background: none;
  border: none;
  text-align: left;
  color: inherit;
  font-family: inherit;
  cursor: pointer;
}
.toprated-rank {
  position: absolute;
  top: 6px;
  left: 6px;
  z-index: 2;
  background: rgba(10, 10, 10, 0.75);
  color: #d68a34;
  font-size: 0.7rem;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 5px;
  font-variant-numeric: tabular-nums;
}
.toprated-art {
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 2 / 3;
  border-radius: 8px;
  background-size: cover;
  background-position: center;
  background-color: #222222;
  border: 1px solid #202020;
  transition: transform 0.2s ease;
}
.toprated-card:hover .toprated-art {
  transform: scale(1.04);
}
.toprated-initial {
  font-size: 1.6rem;
  font-weight: 800;
  color: #444;
}
.toprated-title {
  display: -webkit-box;
  margin-top: 6px;
  font-size: 0.76rem;
  font-weight: 700;
  line-height: 1.25;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.toprated-score {
  display: block;
  margin-top: 2px;
  font-size: 0.74rem;
  font-weight: 700;
  color: #d68a34;
  font-variant-numeric: tabular-nums;
}
</style>
