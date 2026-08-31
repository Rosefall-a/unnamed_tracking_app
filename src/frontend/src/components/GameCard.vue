<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { Game } from '../types/game'

defineProps<{
  game: Game
}>()
</script>

<template>
  <RouterLink :to="`/game/${game.id}`" class="game-card">
    <div 
      class="cover" 
      :style="{ backgroundImage: game.coverImageUrl ? `url(${game.coverImageUrl})` : 'none' }"
    >
      <span v-if="!game.coverImageUrl" class="no-cover">{{ game.title }}</span>
    </div>
    <div class="info">
      <h3 class="title">{{ game.title }}</h3>
      <div class="meta">
        <span class="status">{{ game.status }}</span>
        <span v-if="game.ratingOverall" class="rating">★ {{ game.ratingOverall.toFixed(1) }}</span>
      </div>
    </div>
  </RouterLink>
</template>

<style scoped>
.game-card {
  display: flex;
  flex-direction: column;
  background: #1e1e1e;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  transition: transform 0.15s ease, border-color 0.15s ease;
}

.game-card:hover {
  transform: translateY(-4px);
  border-color: #f5c518;
}

.cover {
  height: 240px;
  background-size: cover;
  background-position: center;
  background-color: #2a2a2a;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  text-align: center;
}

.no-cover {
  color: #777;
  font-weight: 600;
}

.info {
  padding: 12px;
}

.title {
  margin: 0 0 8px;
  font-size: 1rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  color: #aaa;
}

.rating {
  color: #f5c518;
}
</style>