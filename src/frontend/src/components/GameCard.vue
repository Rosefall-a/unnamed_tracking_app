<script setup lang="ts">
import type { Game } from '../types/game'

defineProps<{
  game: Game
}>()
</script>

<template>
  <router-link :to="`/games/${game.id}`" class="game-card">
    <div
      class="cover"
      :style="{ backgroundColor: game.coverColor, backgroundImage: `url(${game.coverImageUrl})` }"
    ></div>
    <div class="info">
      <h3 class="title">{{ game.title }}</h3>
      <div class="meta">
        <span class="status">{{ game.status }}</span>
        <span v-if="game.ratingOverall !== null" class="rating">
          ★ {{ game.ratingOverall.toFixed(1) }}
        </span>
      </div>
      <div class="achievements">🏆 {{ game.achievementPercent }}%</div>
    </div>
  </router-link>
</template>

<style scoped>
.game-card {
  display: block;
  width: 200px;
  border-radius: 8px;
  overflow: hidden;
  background: #1e1e1e;
  color: #fff;
  font-family: system-ui, sans-serif;
  text-decoration: none;
}
.cover {
  height: 280px;
  /* coverColor stays as the background underneath — if coverImageUrl
     ever fails to load, the flat color still shows instead of blank white */
  background-size: cover;
  background-position: center;
}
.info {
  padding: 10px 12px;
}
.title {
  margin: 0 0 6px;
  font-size: 14px;
  color: #fff;
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
.achievements {
  margin-top: 6px;
  font-size: 12px;
  color: #8fd694;
}
</style>