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

// two stacked layers, cross-faded — CSS can't transition a background-image
// swap directly, so each hover alternates which layer is "on top"
const bgLayers = ref<{ url: string | null; visible: boolean }[]>([
  { url: null, visible: false },
  { url: null, visible: false },
])
const activeLayer = ref(0)

function setHoverImage(url: string | null) {
  if (url === null) {
    bgLayers.value[activeLayer.value].visible = false
    return
  }
  const nextLayer = activeLayer.value === 0 ? 1 : 0
  bgLayers.value[nextLayer] = { url, visible: true }
  bgLayers.value[activeLayer.value].visible = false
  activeLayer.value = nextLayer
}

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
    <div
      v-for="(layer, i) in bgLayers"
      :key="i"
      class="ambient-bg"
      :class="{ visible: layer.visible }"
      :style="layer.url ? { backgroundImage: `url(${layer.url})` } : {}"
    ></div>

    <div class="content">
      <div class="header-row">
        <h1>My Games</h1>
        <button type="button" class="add-button" @click="showAddModal = true">+ Add Game</button>
      </div>
      <p v-if="loading">Loading…</p>
      <p v-else-if="error" class="error">{{ error }}</p>
      <div v-else class="grid">
        <GameCard v-for="game in games" :key="game.id" :game="game" @hover="setHoverImage" />
      </div>

      <GameFormModal v-if="showAddModal" @close="showAddModal = false" @saved="onGameCreated" />
    </div>
  </main>
</template>

<style scoped>
.library {
  position: relative;
  padding: 24px;
  font-family: system-ui, sans-serif;
  background: #121212;
  min-height: 100vh;
  color: #fff;
  overflow: hidden;
}
.ambient-bg {
  position: fixed;
  inset: 0;
  background-size: cover;
  background-position: center;
  filter: blur(90px);
  opacity: 0;
  transform: scale(1.2);
  transition: opacity 0.6s ease;
  z-index: 0;
}
.ambient-bg.visible {
  opacity: 0.35;
}
.content {
  position: relative;
  z-index: 1;
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