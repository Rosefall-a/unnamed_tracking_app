<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { mockGames } from '../data/mockGames'
import type { Achievement } from '../types/game'

const route = useRoute()

const game = computed(() => mockGames.find((g) => g.id === route.params.id))

function sortedAchievements(achievements: Achievement[]) {
  return [...achievements].sort((a, b) => {
    if (a.unlockedAt === null && b.unlockedAt === null) return 0
    if (a.unlockedAt === null) return 1
    if (b.unlockedAt === null) return -1
    return b.unlockedAt.localeCompare(a.unlockedAt)
  })
}

function formatPlaytime(minutes: number) {
  if (minutes === 0) return 'Not played yet'
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
}
</script>

<template>
  <main v-if="game" class="detail">
    <section class="hero" :style="{ backgroundColor: game.coverColor }">
      <h1>{{ game.title }}</h1>
      <p class="meta">
        <span class="status">{{ game.status }}</span>
        <span v-if="game.ratingOverall !== null"> · ★ {{ game.ratingOverall.toFixed(1) }}</span>
      </p>
    </section>

    <section class="overview">
      <p v-if="game.description" class="description">{{ game.description }}</p>
      <p class="credits">{{ game.developer }} · {{ game.publisher }}</p>
      <ul class="tags">
        <li v-for="tag in game.tags" :key="tag">{{ tag }}</li>
      </ul>
      <p class="playtime">
        {{ formatPlaytime(game.playtimeMinutes) }}
        <span v-if="game.lastPlayedAt">
          · last played {{ new Date(game.lastPlayedAt).toLocaleDateString() }}
        </span>
      </p>
    </section>

    <section class="achievements">
      <div class="achievements-header">
        <h2>Achievements</h2>
        <span class="percent">{{ game.achievementPercent }}%</span>
      </div>
      <ul class="achievement-list">
        <li
          v-for="achievement in sortedAchievements(game.achievements)"
          :key="achievement.id"
          :class="{ unlocked: achievement.unlockedAt !== null }"
        >
          {{ achievement.unlockedAt !== null ? '✓' : '○' }} {{ achievement.name }}
        </li>
      </ul>
    </section>
  </main>

  <main v-else class="not-found">
    <p>Game not found.</p>
  </main>
</template>

<style scoped>
.detail {
  font-family: system-ui, sans-serif;
  color: #fff;
  min-height: 100vh;
  background: #121212;
}
.hero {
  padding: 48px 24px;
}
.hero h1 {
  margin: 0;
}
.meta {
  text-transform: capitalize;
  color: #ddd;
}
.overview {
  padding: 24px;
  border-bottom: 1px solid #2a2a2a;
}
.description {
  margin: 0 0 12px;
  color: #ddd;
}
.credits {
  margin: 0 0 12px;
  color: #999;
  font-size: 14px;
}
.tags {
  list-style: none;
  display: flex;
  gap: 8px;
  padding: 0;
  margin: 0 0 12px;
  flex-wrap: wrap;
}
.tags li {
  background: #2a2a2a;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
}
.playtime {
  color: #999;
  font-size: 14px;
  margin: 0;
}
.achievements {
  padding: 24px;
}
.achievements-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.percent {
  color: #f5c518;
}
.achievement-list {
  list-style: none;
  padding: 0;
  margin-top: 16px;
}
.achievement-list li {
  padding: 6px 0;
  color: #777;
}
.achievement-list li.unlocked {
  color: #fff;
}
.not-found {
  padding: 24px;
  color: #fff;
}
</style>