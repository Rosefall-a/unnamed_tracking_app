<script setup lang="ts">
import { computed } from 'vue'
import type { Game } from '../types/game'

const props = defineProps<{
  name: string
  games: Game[]
}>()

const emit = defineEmits<{
  open: [name: string]
}>()

const covers = computed(() => props.games.slice(0, 4).map((g) => g.coverImageUrl))
const emptySlots = computed(() => Math.max(0, 4 - covers.value.length))
</script>

<template>
  <div class="collection-card-wrap" @click="emit('open', name)">
    <div class="collection-card">
      <div class="cover">
        <div class="cover-grid">
          <div
            v-for="(cover, i) in covers"
            :key="i"
            class="cover-cell"
            :style="{ backgroundImage: `url(${cover})` }"
          ></div>
          <div v-for="i in emptySlots" :key="`empty-${i}`" class="cover-cell empty"></div>
        </div>
      </div>
    </div>

    <div class="card-info">
      <h3 class="title">{{ name }}</h3>
      <div class="meta-row">
        <span class="status">{{ games.length }} game{{ games.length === 1 ? '' : 's' }}</span>
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
  transition: transform 0.32s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.32s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform;
}
.collection-card-wrap:hover .collection-card {
  transform: scale(1.07) translateY(-4px);
  box-shadow: 0 24px 56px rgba(0, 0, 0, 0.5);
}
.cover {
  position: relative;
  width: 100%;
  /* matches GameCard's 2:3 (Steam-vertical) ratio so collection cards stay
     uniform with regular game cards */
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
.card-info {
  padding: 10px 2px 0;
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
  color: #999;
}
</style>
