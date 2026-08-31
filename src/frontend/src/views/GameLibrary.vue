<script setup lang="ts">
import { ref, onMounted } from 'vue'
import GameCard from '../components/GameCard.vue'
import { fetchGames } from '../services/games'
import type { Game } from '../types/game'

const games = ref<Game[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    games.value = await fetchGames()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load games'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="library">
    <h1>My Games</h1>
    <p v-if="loading">Loading…</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <div v-else class="grid">
      <GameCard v-for="game in games" :key="game.id" :game="game" />
    </div>
  </main>
</template>

<style scoped>
.library {
  padding: 24px;
  font-family: system-ui, sans-serif;
  background: #121212;
  min-height: 100vh;
  color: #fff;
}
.grid {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.error {
  color: #f87171;
}
</style>