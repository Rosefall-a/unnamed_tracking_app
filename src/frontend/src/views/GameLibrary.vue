<script setup lang="ts">
import { ref, onMounted } from 'vue'
import GameCard from '../components/GameCard.vue'
import type { Game } from '../types/game'
import { MOCK_GAMES } from '../data/mockGames'

const games = ref<Game[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    // Replace with backend fetch when API is operational
    games.value = MOCK_GAMES
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="library">
    <h1>My Games</h1>
    <div v-if="loading" class="loading">Loading library…</div>
    <div v-else class="game-grid">
      <GameCard v-for="game in games" :key="game.id" :game="game" />
    </div>
  </div>
</template>

<style scoped>
.library {
  padding: 24px;
  color: #fff;
  background: #121212;
  min-height: 100vh;
}
.game-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 20px;
  margin-top: 20px;
}
</style>