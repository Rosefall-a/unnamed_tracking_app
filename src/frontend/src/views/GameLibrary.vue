<script setup lang="ts">
import GameCard from '../components/GameCard.vue'
import { mockGames } from '../data/mockGames.ts'
</script>

<template>
  <main class="library">
    <h1>My Games</h1>
    <div class="grid">
      <GameCard v-for="game in mockGames" :key="game.id" :game="game" />
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
</style>