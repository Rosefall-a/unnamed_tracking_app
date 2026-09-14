<script setup lang="ts">
import { currentUser } from "../state/auth";
</script>

<template>
  <router-link
    v-if="currentUser"
    to="/settings?section=profile"
    class="profile-dock"
    aria-label="Open your profile"
  >
    <span class="avatar">{{ currentUser.username.slice(0, 2).toUpperCase() }}</span>
    <span class="name">{{ currentUser.username }}</span>
  </router-link>
</template>

<style scoped>
.profile-dock {
  position: fixed;
  left: 14px;
  bottom: 14px;
  z-index: 111;
  width: 242px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  background: #161616;
  color: #fff;
  text-decoration: none;
  font: 600 13px/1.2 system-ui, sans-serif;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}
.profile-dock:hover { background: #202020; border-color: #444; }
.avatar { width: 30px; height: 30px; flex: 0 0 30px; display: grid; place-items: center; border-radius: 50%; background: #d68a34; color: #111; font-size: 11px; font-weight: 800; }
.name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 700px) { .profile-dock { left: 10px; bottom: 10px; width: 220px; } }
</style>
