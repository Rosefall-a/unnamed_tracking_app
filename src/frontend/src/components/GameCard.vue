<script setup lang="ts">
import type { Game } from '../types/game'

defineProps<{
  game: Game
}>()
</script>

<template>
  <article class="game-card">
    <div class="cover" :style="{ backgroundColor: game.coverColor }">
      {{ game.title }}
    </div>
    <div class="info">
      <h3 class="title">{{ game.title }}</h3>
      <div class="meta">
        <span class="status">{{ game.status }}</span>
        <span v-if="game.ratingOverall !== null" class="rating">
          ★ {{ game.ratingOverall.toFixed(1) }}
        </span>
      </div>
    </div>
  </article>
</template>

<style scoped>
.game-card {
  width: 200px;
  border-radius: 8px;
  overflow: hidden;
  background: #1e1e1e;
  color: #fff;
  font-family: system-ui, sans-serif;
}
.cover {
  height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  text-align: center;
  font-weight: 600;
}
.info {
  padding: 10px 12px;
}
.title {
  margin: 0 0 6px;
  font-size: 14px;
}
.meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #aaa;
}
.status {
  text-transform: capitalize;
}
.rating {
  color: #f5c518;
}
</style>