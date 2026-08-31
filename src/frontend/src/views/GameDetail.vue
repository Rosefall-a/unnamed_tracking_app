<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { mockGames } from '../data/mockGames'
import type { Achievement } from '../types/game'

const route = useRoute()

const game = computed(() => mockGames.find((g) => g.id === route.params.id))

const tabs = ['Overview', 'Achievements', 'Screenshots', 'Clips', 'Saves', 'Docs', 'Notes', 'Stats'] as const
const activeTab = ref<(typeof tabs)[number]>('Overview')

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
      <!-- .hero itself stays full-width so the color bleeds edge to edge;
           this inner wrapper is what actually gets capped and centered -->
      <div class="hero-inner">
        <div class="hero-top">
          <h1>{{ game.title }}</h1>
          <button class="edit-button" type="button">Edit</button>
        </div>
        <p class="meta">
          <span class="status">{{ game.status }}</span>
          <span v-if="game.ratingOverall !== null"> · ★ {{ game.ratingOverall.toFixed(1) }}</span>
        </p>
      </div>
    </section>

    <nav class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab"
        type="button"
        class="tab"
        :class="{ active: activeTab === tab }"
        @click="activeTab = tab"
      >
        {{ tab }}
      </button>
    </nav>

    <section v-if="activeTab === 'Overview'" class="overview">
      <div class="overview-main">
        <p v-if="game.description" class="description">{{ game.description }}</p>
        <ul class="tags">
          <li v-for="tag in game.tags" :key="tag">{{ tag }}</li>
        </ul>
        <ul class="platforms">
          <li v-for="p in game.platforms" :key="p.platform">
            <span class="platform-name">{{ p.platform }}</span>
            <span>{{ formatPlaytime(p.playtimeMinutes) }}</span>
            <span v-if="p.completionPercent !== null">{{ p.completionPercent }}%</span>
            <span v-if="p.lastPlayedAt">
              last played {{ new Date(p.lastPlayedAt).toLocaleDateString() }}
            </span>
          </li>
        </ul>
      </div>

      <aside class="details-panel">
        <div class="detail-row">
          <span class="detail-label">Series</span>
          <span class="detail-value">{{ game.series ?? '—' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Developer</span>
          <span class="detail-value">{{ game.developer ?? '—' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Publisher</span>
          <span class="detail-value">{{ game.publisher ?? '—' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Date Added</span>
          <span class="detail-value">
            {{ game.dateAdded ? new Date(game.dateAdded).toLocaleDateString() : '—' }}
          </span>
        </div>
      </aside>
    </section>

    <section v-else-if="activeTab === 'Achievements'" class="achievements">
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

    <section v-else class="coming-soon">
      <p>{{ activeTab }} coming soon.</p>
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
.hero-inner {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
}
.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
.hero-top h1 {
  margin: 0;
}
.edit-button {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
}
.meta {
  text-transform: capitalize;
  color: #ddd;
}
.tabs {
  display: flex;
  gap: 4px;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 0 24px;
  box-sizing: border-box;
  border-bottom: 1px solid #2a2a2a;
  overflow-x: auto;
}
.tab {
  background: none;
  border: none;
  color: #999;
  padding: 12px 14px;
  font-size: 14px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
}
.tab.active {
  color: #fff;
  border-bottom-color: #f5c518;
}
.overview {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 24px;
  align-items: start;
}
.description {
  margin: 0 0 12px;
  color: #ddd;
}
.tags {
  list-style: none;
  display: flex;
  gap: 8px;
  padding: 0;
  margin: 0 0 16px;
  flex-wrap: wrap;
}
.tags li {
  background: #2a2a2a;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
}
.details-panel {
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 4px 16px;
}
.detail-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 0;
  font-size: 14px;
  border-bottom: 1px solid #202020;
}
.detail-row:last-child {
  border-bottom: none;
}
.detail-label {
  color: #999;
}
.detail-value {
  color: #fff;
}
.platforms {
  list-style: none;
  padding: 0;
  margin: 0;
}
.platforms li {
  display: flex;
  gap: 12px;
  padding: 4px 0;
  color: #999;
  font-size: 14px;
}
.platform-name {
  color: #fff;
  font-weight: 600;
  min-width: 90px;
}
.achievements {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px;
  box-sizing: border-box;
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
.coming-soon {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 48px 24px;
  box-sizing: border-box;
  color: #777;
  text-align: center;
}
.not-found {
  padding: 24px;
  color: #fff;
}
@media (max-width: 800px) {
  .overview {
    grid-template-columns: 1fr;
  }
}
</style>