<script setup lang="ts">
// The one sticky top bar every page in the Media area and the Calendar and
// Statistics pages share: fixed minimum height, padding, border and the
// profile chip live here once, so nothing shifts when you move between
// pages. Callers fill the left side (default slot) and, optionally, the
// right-hand `actions` slot.
import { currentUser } from "../state/auth";
</script>

<template>
  <div class="media-topbar">
    <div class="topbar-left"><slot /></div>
    <div v-if="$slots.actions" class="media-topbar-actions">
      <slot name="actions" />
    </div>
    <div v-if="currentUser" class="profile-chip">
      <span class="profile-name">{{ currentUser.username }}</span>
      <div class="profile-avatar">
        {{ currentUser.username.slice(0, 2).toUpperCase() }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.media-topbar {
  position: sticky;
  top: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  gap: 16px;
  box-sizing: border-box;
  min-height: 68px;
  padding: 10px 16px 10px 64px;
  background: rgba(13, 13, 13, 0.94);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid #202020;
}
.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  min-width: 0;
}
.media-topbar-actions {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  min-width: 0;
  gap: 10px;
}
/* With no actions slot the chip still needs to sit at the far right */
.profile-chip {
  margin-left: auto;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(20, 20, 20, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 999px;
  padding: 6px 6px 6px 16px;
}
.media-topbar-actions + .profile-chip {
  margin-left: 0;
}
.profile-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #d68a34;
  color: #111;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}
.profile-name {
  color: #fff;
  font-size: 13px;
  font-weight: 600;
}
@media (max-width: 720px) {
  .media-topbar {
    padding-left: 60px;
    flex-wrap: wrap;
  }
  .profile-name {
    display: none;
  }
  .profile-chip {
    padding-left: 6px;
  }
}
</style>
