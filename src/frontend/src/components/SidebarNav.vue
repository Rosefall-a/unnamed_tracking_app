<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const open = ref(false)

function isActive(path: string) {
  return route.path === path
}

function close() {
  open.value = false
}
</script>

<template>
  <button type="button" class="menu-toggle" @click="open = true">
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  </button>

  <Transition name="sidebar-backdrop">
    <div v-if="open" class="sidebar-backdrop" @click="close"></div>
  </Transition>

  <Transition name="sidebar-slide">
    <aside v-if="open" class="sidebar">
      <div class="sidebar-brand">
        <div class="brand-icon">🎮</div>
        <span class="brand-name">Archive</span>
      </div>

      <router-link to="/profile" class="sidebar-item" @click="close">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="8" r="4" />
          <path d="M4 20c0-4.4 3.6-7 8-7s8 2.6 8 7" />
        </svg>
        <span>Profile</span>
      </router-link>

      <div class="sidebar-divider"></div>

      <router-link to="/" class="sidebar-item" :class="{ active: isActive('/') }" @click="close">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 11l9-8 9 8" />
          <path d="M5 10v10h14V10" />
        </svg>
        <span>Home</span>
      </router-link>

      <router-link to="/games" class="sidebar-item" :class="{ active: isActive('/games') }" @click="close">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="7" width="20" height="10" rx="4" />
          <line x1="7" y1="12" x2="9" y2="12" />
          <line x1="8" y1="11" x2="8" y2="13" />
          <circle cx="16" cy="11" r="0.8" fill="currentColor" />
          <circle cx="18" cy="13" r="0.8" fill="currentColor" />
        </svg>
        <span>Games</span>
      </router-link>

      <div class="sidebar-item disabled">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="4" width="18" height="16" rx="2" />
          <line x1="3" y1="9" x2="21" y2="9" />
        </svg>
        <span>Movies & TV</span>
        <span class="soon-badge">soon</span>
      </div>

      <div class="sidebar-spacer"></div>

      <div class="sidebar-item disabled">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.5 1z" />
        </svg>
        <span>Settings</span>
        <span class="soon-badge">soon</span>
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
.menu-toggle {
  position: fixed;
  top: 16px;
  left: 16px;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(20, 20, 20, 0.55);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 100;
  transition: background 0.15s ease;
}
.menu-toggle:hover {
  background: rgba(40, 40, 40, 0.85);
}
.sidebar-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  z-index: 105;
}
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 270px;
  background: #161616;
  border-right: 1px solid #2a2a2a;
  z-index: 110;
  display: flex;
  flex-direction: column;
  padding: 20px 14px;
  font-family: system-ui, sans-serif;
  box-shadow: 12px 0 40px rgba(0, 0, 0, 0.4);
}
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 10px 18px;
}
.brand-icon {
  font-size: 22px;
}
.brand-name {
  color: #fff;
  font-weight: 700;
  font-size: 16px;
}
.sidebar-divider {
  height: 1px;
  background: #2a2a2a;
  margin: 8px 10px 12px;
}
.sidebar-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  color: #ccc;
  text-decoration: none;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.sidebar-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}
.sidebar-item.active {
  background: rgba(214, 138, 52, 0.14);
  color: #d68a34;
}
.sidebar-item.disabled {
  color: #555;
  cursor: not-allowed;
}
.sidebar-item.disabled:hover {
  background: none;
}
.soon-badge {
  margin-left: auto;
  font-size: 10px;
  color: #777;
  background: rgba(255, 255, 255, 0.06);
  padding: 2px 6px;
  border-radius: 999px;
}
.sidebar-spacer {
  flex: 1;
}
.sidebar-slide-enter-active,
.sidebar-slide-leave-active {
  transition: transform 0.25s ease;
}
.sidebar-slide-enter-from,
.sidebar-slide-leave-to {
  transform: translateX(-100%);
}
.sidebar-backdrop-enter-active,
.sidebar-backdrop-leave-active {
  transition: opacity 0.25s ease;
}
.sidebar-backdrop-enter-from,
.sidebar-backdrop-leave-to {
  opacity: 0;
}
</style>