<script setup lang="ts">
import { currentUser } from "../state/auth";
</script>

<template>
  <router-link
    v-if="currentUser"
    to="/settings?section=profile"
    class="profile-chip-global"
    aria-label="Open your profile"
  >
    <span class="profile-name">{{ currentUser.username }}</span>
    <span class="profile-avatar">{{ currentUser.username.slice(0, 2).toUpperCase() }}</span>
  </router-link>
</template>

<style scoped>
.profile-chip-global{position:fixed;top:16px;right:18px;z-index:109;display:flex;align-items:center;gap:9px;padding:6px 8px 6px 11px;border:1px solid rgba(255,255,255,.12);border-radius:999px;background:rgba(20,20,20,.72);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);color:#ddd;text-decoration:none;font:600 12px/1 system-ui,sans-serif;box-shadow:0 6px 20px rgba(0,0,0,.22);transition:background .15s ease,border-color .15s ease,transform .15s ease}.profile-chip-global:hover{background:#202020;border-color:#444;color:#fff;transform:translateY(-1px)}.profile-name{max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.profile-avatar{width:30px;height:30px;display:grid;place-items:center;border-radius:50%;background:#d68a34;color:#111;font-size:10px;font-weight:800}@media(max-width:1024px){.profile-chip-global{top:14px;right:14px}}@media(max-width:520px){.profile-name{max-width:110px}}
</style>
