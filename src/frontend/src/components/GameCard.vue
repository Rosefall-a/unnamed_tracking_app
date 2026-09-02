<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { Game, GameStatus } from '../types/game'
import { setFavorite, setStatus } from '../services/games'
import { ref, computed, nextTick } from 'vue'

const props = defineProps<{
  game: Game
}>()

const emit = defineEmits<{
  edit: [game: Game]
  delete: [game: Game]
  'add-to-collection': [game: Game]
  hover: [coverUrl: string | null]
}>()

const router = useRouter()

const menuOpen = ref(false)
const statusSubmenuOpen = ref(false)
const localFavorite = ref(props.game.favorite)
const favoriteSaving = ref(false)

const menuTriggerRef = ref<HTMLElement | null>(null)
const menuPosition = ref({ top: 0, left: 0 })

function onWindowScroll() {
  closeMenu()
}

async function toggleMenu() {
  menuOpen.value = !menuOpen.value
  if (menuOpen.value && menuTriggerRef.value) {
    await nextTick()
    const rect = menuTriggerRef.value.getBoundingClientRect()
    menuPosition.value = { top: rect.bottom + 6, left: rect.right - 190 }
    window.addEventListener('scroll', onWindowScroll, true)
  } else {
    window.removeEventListener('scroll', onWindowScroll, true)
  }
}

function closeMenu() {
  menuOpen.value = false
  statusSubmenuOpen.value = false
  window.removeEventListener('scroll', onWindowScroll, true)
}

const statuses: GameStatus[] = [
  'wishlist',
  'backlog',
  'playing',
  'on hold',
  'beaten',
  'played',
  'dropped',
  'mastered',
]

function openGame() {
  router.push(`/games/${props.game.id}`)
}

async function toggleFavorite() {
  const next = !localFavorite.value
  localFavorite.value = next
  favoriteSaving.value = true
  try {
    await setFavorite(props.game.id, next)
  } catch {
    localFavorite.value = !next
  } finally {
    favoriteSaving.value = false
  }
}

async function chooseStatus(status: GameStatus) {
  try {
    await setStatus(props.game.id, status)
    props.game.status = status
  } catch {
    // silently ignore — card just keeps showing the old status
  }
  closeMenu()
}

function copyFolderPath() {
  if (props.game.folderLocation) {
    navigator.clipboard.writeText(props.game.folderLocation)
  }
  closeMenu()
}

</script>

<template>
<div class="game-card-wrap" @mouseenter="emit('hover', game.bannerImageUrl || game.coverImageUrl)">
    <div class="game-card" :class="{ 'menu-open': menuOpen }">
      <div class="cover" @click="openGame">
        <img class="cover-image" :src="game.coverImageUrl" :alt="game.title" />
      </div>

<button type="button" class="collection-button" @click.stop="emit('add-to-collection', game)">
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
  </svg>
</button>

<button
  type="button"
  class="favorite-button"
  :class="{ active: localFavorite }"
  :disabled="favoriteSaving"
  @click.stop="toggleFavorite"
>
  <svg
    viewBox="0 0 24 24"
    width="16"
    height="16"
    :fill="localFavorite ? 'currentColor' : 'none'"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
  >
    <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.6z" />
  </svg>
</button>

<button type="button" class="menu-trigger" ref="menuTriggerRef" @click.stop="toggleMenu">
  <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
    <circle cx="5" cy="12" r="2" />
    <circle cx="12" cy="12" r="2" />
    <circle cx="19" cy="12" r="2" />
  </svg>
</button>

<Teleport to="body">
  <div v-if="menuOpen" class="menu-backdrop" @click="closeMenu"></div>
  <Transition name="menu-pop">
    <div v-if="menuOpen" class="card-menu" :style="{ top: menuPosition.top + 'px', left: menuPosition.left + 'px' }" @click.stop>
          <template v-if="!statusSubmenuOpen">
            <button type="button" class="menu-item" @click="openGame">Open</button>
            <div class="menu-divider"></div>
            <button type="button" class="menu-item" @click="emit('edit', game); closeMenu()">Edit</button>
            <button type="button" class="menu-item" @click="statusSubmenuOpen = true">Change Status</button>
            <button type="button" class="menu-item disabled" disabled>Refresh Metadata</button>
            <div class="menu-divider"></div>
            <button type="button" class="menu-item disabled" disabled>Add Screenshot</button>
            <button type="button" class="menu-item disabled" disabled>Add Clip</button>
            <div class="menu-divider"></div>
            <button type="button" class="menu-item" @click="copyFolderPath">Copy Folder Path</button>
            <div class="menu-divider"></div>
            <button type="button" class="menu-item destructive" @click="emit('delete', game); closeMenu()">
              Delete
            </button>
          </template>
          <template v-else>
            <button type="button" class="menu-item back" @click="statusSubmenuOpen = false">← Back</button>
            <div class="menu-divider"></div>
            <button
              v-for="s in statuses"
              :key="s"
              type="button"
              class="menu-item"
              :class="{ active: s === game.status }"
              @click="chooseStatus(s)"
            >
              {{ s }}
            </button>
          </template>
        </div>
            </Transition>
    </Teleport>
    </div>

    <div class="card-info">
      <h3 class="title">{{ game.title }}</h3>
      <div class="meta-row">
        <span class="status">{{ game.status }}</span>
        <span v-if="game.ratingOverall !== null" class="rating">★ {{ game.ratingOverall.toFixed(1) }}</span>
        <span v-if="game.achievementPercent > 0" class="achievements">🏆 {{ game.achievementPercent }}%</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.game-card-wrap {
  width: 200px;
}
.game-card {
  position: relative;
  width: 100%;
  border-radius: 10px;
  transition: transform 0.32s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.32s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform;
  z-index: 1;
}
.game-card:hover,
.game-card.menu-open {
  transform: scale(1.07) translateY(-4px);
  box-shadow: 0 24px 56px rgba(0, 0, 0, 0.5);
  z-index: 10;
}
.cover {
  position: relative;
  width: 100%;
  height: 280px;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  background: #1a1a1a;
}
.cover-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.favorite-button,
.collection-button,
.menu-trigger {
  position: absolute;
  top: 8px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(20, 20, 20, 0.55);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transform: translateY(-4px);
  transition: opacity 0.2s ease, transform 0.2s ease, background 0.15s ease, color 0.15s ease,
    border-color 0.15s ease;
  z-index: 3;
}
.game-card:hover .favorite-button,
.game-card:hover .collection-button,
.game-card:hover .menu-trigger,
.game-card.menu-open .favorite-button,
.game-card.menu-open .collection-button,
.game-card.menu-open .menu-trigger {
  opacity: 1;
  transform: translateY(0);
}
.collection-button {
  right: 78px;
}
.favorite-button {
  right: 44px;
}
.menu-trigger {
  right: 8px;
}
.favorite-button.active {
  opacity: 1;
  transform: translateY(0);
  color: #ff6f91;
  border-color: rgba(255, 111, 145, 0.4);
  background: rgba(224, 86, 122, 0.18);
}
.menu-trigger:hover,
.favorite-button:hover,
.collection-button:hover {
  background: rgba(40, 40, 40, 0.85);
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(0) scale(1.08);
}
.menu-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
}
.card-menu {
  position: fixed;
  width: 190px;
  background: #1e1e1e;
  border: 1px solid #333;
  border-radius: 10px;
  padding: 6px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
  z-index: 30;
  display: flex;
  flex-direction: column;
  gap: 2px;
  transform-origin: top right;
}
.menu-pop-enter-active,
.menu-pop-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.menu-pop-enter-from,
.menu-pop-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.96);
}
.menu-item {
  text-align: left;
  background: none;
  border: none;
  color: #ddd;
  padding: 8px 10px;
  font-size: 13px;
  border-radius: 6px;
  cursor: pointer;
  text-transform: capitalize;
}
.menu-item:hover:not(.disabled) {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.menu-item.disabled {
  color: #555;
  cursor: not-allowed;
}
.menu-item.destructive {
  color: #f87171;
}
.menu-item.destructive:hover {
  background: rgba(220, 38, 38, 0.15);
}
.menu-item.active {
  color: #d68a34;
  font-weight: 600;
}
.menu-item.back {
  color: #999;
}
.menu-divider {
  height: 1px;
  background: #2a2a2a;
  margin: 4px 2px;
}
.card-info {
  padding: 10px 2px 0;
}
.title {
  margin: 0 0 2px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta-row {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #999;
}
.meta-row .status {
  text-transform: capitalize;
}
.meta-row .rating {
  color: #d68a34;
}
</style>