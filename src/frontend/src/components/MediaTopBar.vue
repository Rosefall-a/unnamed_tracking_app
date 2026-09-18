<script setup lang="ts">
// The one sticky top bar every Media-section page shares (Movies/TV/Anime
// libraries, Calendar, Lists). It used to be copied into each page, and
// the copies drifted: the library's bar was taller than the others because
// it carried the layout tabs, and its profile chip floated separately.
// Now the height, padding, border and profile chip live here once; a page
// only decides what goes in the right-hand `actions` slot.
import { currentUser } from "../state/auth";
import MediaKindSwitch from "./MediaKindSwitch.vue";

defineProps<{
  active: "movie" | "tv" | "anime" | "calendar" | "lists";
  // sub-pages (a single list) get a back arrow ahead of the switcher
  back?: boolean;
}>();
defineEmits<{ back: [] }>();
</script>

<template>
  <div class="media-topbar">
    <button v-if="back" type="button" class="topbar-back" title="Back" @click="$emit('back')">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 12H5" />
        <path d="M12 19l-7-7 7-7" />
      </svg>
    </button>
    <MediaKindSwitch :active="active" />
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
.topbar-back {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(20, 20, 20, 0.55);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease;
}
.topbar-back:hover {
  background: rgba(40, 40, 40, 0.85);
}
.media-topbar-actions {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
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
