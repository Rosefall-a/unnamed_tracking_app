<script setup lang="ts">
import { ref, onMounted } from 'vue'
import GameCard from '../components/GameCard.vue'
import GameFormModal from '../components/GameFormModal.vue'
import { fetchGames } from '../services/games'
import type { Game } from '../types/game'

const games = ref<Game[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const showAddModal = ref(false)

async function loadGames() {
  loading.value = true
  try {
    games.value = await fetchGames()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load games'
  } finally {
    loading.value = false
  }
}

onMounted(loadGames)

async function onGameCreated() {
  showAddModal.value = false
  await loadGames()
}
</script>

<template>
  <main class="library">
    <div class="header-row">
      <h1>My Games</h1>
      <button type="button" class="add-button" @click="showAddModal = true">+ Add Game</button>
    </div>
    <p v-if="loading">Loading…</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <div v-else class="grid">
      <GameCard v-for="game in games" :key="game.id" :game="game" />
    </div>

    <GameFormModal v-if="showAddModal" @close="showAddModal = false" @saved="onGameCreated" />
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
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.add-button {
  background: #d68a34;
  color: #111;
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-weight: 600;
  cursor: pointer;
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