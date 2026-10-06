<script setup lang="ts">
// The bell + name + avatar chip. One component, one position: 11px from
// the top and 16px from the right on every page, so it never shifts as
// the window resizes or the page around it changes. Pages with the shared
// top bar get it through AppTopBar; the rest use the `fixed` form.
import { currentUser } from "../state/auth";
import NotificationBell from "./NotificationBell.vue";
import ProfileMenu from "./ProfileMenu.vue";
import { navigationViewport } from "../state/sidebarMode";

defineProps<{ fixed?: boolean; inline?: boolean }>();
</script>

<template>
  <div
    v-if="currentUser && (inline || navigationViewport !== 'phone')"
    class="account-chip"
    :class="{ fixed, inline }"
  >
    <NotificationBell />
    <ProfileMenu :initials="currentUser.username.slice(0, 2).toUpperCase()">
      <span class="account-name">{{ currentUser.username }}</span>
    </ProfileMenu>
  </div>
</template>

<style scoped>
.account-chip {
  position: absolute;
  top: 11px;
  right: 16px;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 10px;
  box-sizing: border-box;
  height: 46px;
  padding: 6px;
  background: var(--ui-surface);
  border: 1px solid color-mix(in srgb, var(--ui-text) 14%, transparent);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border-radius: 999px;
  color: var(--ui-text);
}
.account-chip.fixed {
  position: fixed;
}
.account-chip.inline {
  position: static;
  flex-shrink: 0;
}
/* Pages disagree about box-sizing, which made the avatar's chevron badge
   15px on some pages and 19px on others. Pin it for everything in the chip. */
.account-chip,
.account-chip :deep(*) {
  box-sizing: border-box;
}
.account-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ui-text);
  font-size: 13px;
  font-weight: 600;
}
@media (max-width: 520px) {
  .account-name {
    display: none;
  }
}
</style>
