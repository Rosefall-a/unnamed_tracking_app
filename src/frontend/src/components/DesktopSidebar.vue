<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import { currentUser } from "../state/auth";
import { logout } from "../services/auth";

const route = useRoute();
const router = useRouter();

function isActive(path: string) {
  return route.path === path || route.path.startsWith(`${path}/`);
}

async function handleLogout() {
  await logout();
  currentUser.value = null;
  router.push("/login");
}
</script>

<template>
  <aside class="desktop-sidebar">
    <div class="desktop-sidebar-brand">
      <span class="brand-icon">🎮</span>
      <span>Archive</span>
    </div>

    <nav class="desktop-sidebar-nav" aria-label="Main navigation">
      <router-link to="/" class="desktop-sidebar-item" :class="{ active: isActive('/') }">
        <span>⌂</span><span>Home</span>
      </router-link>
      <router-link to="/games" class="desktop-sidebar-item" :class="{ active: isActive('/games') }">
        <span>🎮</span><span>Games</span>
      </router-link>
      <router-link to="/collections" class="desktop-sidebar-item" :class="{ active: isActive('/collections') }">
        <span>▣</span><span>Collections</span>
      </router-link>
      <router-link to="/cards" class="desktop-sidebar-item" :class="{ active: isActive('/cards') }">
        <span>▤</span><span>Cards</span>
      </router-link>
      <router-link to="/sets" class="desktop-sidebar-item" :class="{ active: isActive('/sets') }">
        <span>▦</span><span>Sets</span>
      </router-link>
      <router-link to="/inbox" class="desktop-sidebar-item" :class="{ active: isActive('/inbox') }">
        <span>✉</span><span>Inbox</span>
      </router-link>
      <router-link to="/bounties" class="desktop-sidebar-item" :class="{ active: isActive('/bounties') }">
        <span>◎</span><span>Bounties</span>
      </router-link>
    </nav>

    <div class="desktop-sidebar-spacer"></div>

    <router-link to="/settings?section=profile" class="desktop-sidebar-profile">
      <span class="desktop-profile-avatar">{{ currentUser?.username?.slice(0, 2).toUpperCase() }}</span>
      <span class="desktop-profile-copy">
        <strong>{{ currentUser?.username || "Profile" }}</strong>
        <small>Profile</small>
      </span>
    </router-link>
    <router-link to="/settings" class="desktop-sidebar-item" :class="{ active: isActive('/settings') }">
      <span>⚙</span><span>Settings</span>
    </router-link>
    <button type="button" class="desktop-sidebar-logout" @click="handleLogout">
      <span>↪</span><span>Log out</span>
    </button>
  </aside>
</template>

<style scoped>
.desktop-sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 120;
  width: 236px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 18px 12px 14px;
  background: #151515;
  border-right: 1px solid #2a2a2a;
  color: #ccc;
  font-family: system-ui, sans-serif;
}
.desktop-sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 10px 18px;
  color: #fff;
  font-weight: 800;
  font-size: 16px;
}
.brand-icon { font-size: 18px; }
.desktop-sidebar-nav { display: flex; flex-direction: column; gap: 3px; }
.desktop-sidebar-item,
.desktop-sidebar-profile,
.desktop-sidebar-logout {
  min-height: 40px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 9px 10px;
  border-radius: 8px;
  border: 0;
  background: transparent;
  color: #aaa;
  font: inherit;
  font-size: 13px;
  text-decoration: none;
  cursor: pointer;
  text-align: left;
}
.desktop-sidebar-item:hover,
.desktop-sidebar-profile:hover,
.desktop-sidebar-logout:hover,
.desktop-sidebar-item.active {
  color: #fff;
  background: rgba(255,255,255,.06);
}
.desktop-sidebar-item.active { color: #d68a34; }
.desktop-sidebar-spacer { flex: 1; }
.desktop-sidebar-profile { border-top: 1px solid #2a2a2a; border-radius: 0; padding-top: 14px; }
.desktop-profile-avatar {
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #d68a34;
  color: #111;
  font-size: 11px;
  font-weight: 800;
}
.desktop-profile-copy { min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.desktop-profile-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #fff; }
.desktop-profile-copy small { color: #777; font-size: 10px; }
.desktop-sidebar-logout { width: 100%; color: #888; }

@media (max-width: 1024px) {
  .desktop-sidebar { display: none; }
}
</style>
