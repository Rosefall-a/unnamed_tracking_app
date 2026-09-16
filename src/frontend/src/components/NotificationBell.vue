<script setup lang="ts">
import { ref, onMounted } from "vue";
import { notifications, notificationsLoaded, refreshNotifications } from "../state/notifications";

const open = ref(false);
onMounted(refreshNotifications);
</script>

<template>
  <div class="notification-bell">
    <button
      type="button"
      class="bell-button"
      aria-label="Notifications"
      :aria-expanded="open"
      @click="open = !open"
    >
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.7 21a2 2 0 0 1-3.4 0" />
      </svg>
      <span v-if="notifications.length" class="badge">{{ notifications.length }}</span>
    </button>

    <div v-if="open" class="popover">
      <div class="popover-header">
        <strong>Notifications</strong>
        <button type="button" @click="open = false">Close</button>
      </div>
      <p v-if="!notificationsLoaded" class="empty">Loading…</p>
      <p v-else-if="!notifications.length" class="empty">Nothing to flag right now.</p>
      <router-link
        v-for="notification in notifications"
        v-else
        :key="notification.id"
        :to="notification.to"
        class="notification-row"
        @click="open = false"
      >
        <span class="dot" :class="notification.kind"></span>
        <span><strong>{{ notification.title }}</strong><small>{{ notification.detail }}</small></span>
      </router-link>
    </div>
  </div>
</template>

<style scoped>
.notification-bell{position:fixed;top:20px;right:180px;z-index:112}.bell-button{position:relative;width:40px;height:40px;border:1px solid rgba(255,255,255,.12);border-radius:50%;background:rgba(18,18,18,.78);color:#fff;backdrop-filter:blur(8px);cursor:pointer;display:grid;place-items:center}.bell-button:hover{background:#202020;border-color:#444}.badge{position:absolute;top:-4px;right:-4px;min-width:18px;height:18px;padding:0 4px;border-radius:999px;background:#d68a34;color:#111;font:800 10px/18px system-ui,sans-serif;text-align:center}.popover{position:absolute;top:48px;right:0;width:320px;max-height:420px;overflow:auto;border:1px solid #333;border-radius:12px;background:#171717;box-shadow:0 16px 40px rgba(0,0,0,.45);padding:8px}.popover-header{display:flex;align-items:center;justify-content:space-between;padding:8px 8px 10px;color:#fff}.popover-header button{border:0;background:none;color:#999;cursor:pointer}.notification-row{display:flex;gap:9px;padding:9px 8px;border-radius:8px;color:#ddd;text-decoration:none}.notification-row:hover{background:#232323}.notification-row > span:last-child{display:flex;flex-direction:column;gap:2px;min-width:0}.notification-row strong{font-size:12px}.notification-row small{color:#999;font-size:11px;line-height:1.35}.dot{width:8px;height:8px;flex:0 0 8px;margin-top:4px;border-radius:50%;background:#888}.dot.info{background:#60a5fa}.dot.warning{background:#f59e0b}.dot.suggested{background:#d68a34}.empty{padding:18px 10px;color:#999;font-size:12px;text-align:center}@media(max-width:700px){.notification-bell{right:132px}.popover{position:fixed;top:68px;left:10px;right:10px;width:auto}}
</style>
