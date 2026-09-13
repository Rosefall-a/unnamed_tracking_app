<script setup lang="ts">
import { currentUser } from "../state/auth";
</script>
<template>
  <router-link v-if="currentUser" to="/settings?section=profile" class="profile-button" aria-label="Open your profile">
    <span>{{ currentUser.username }}</span>
    <span class="avatar">{{ currentUser.username.slice(0, 2).toUpperCase() }}</span>
  </router-link>
</template>
<style scoped>.profile-button{position:fixed;top:20px;right:28px;z-index:90;display:flex;align-items:center;gap:10px;padding:8px 10px 8px 14px;border:1px solid rgba(255,255,255,.12);border-radius:999px;background:rgba(18,18,18,.78);backdrop-filter:blur(8px);color:#fff;text-decoration:none;font-size:13px;font-weight:600;box-shadow:0 8px 24px rgba(0,0,0,.2)}.profile-button:hover{border-color:rgba(214,138,52,.6);background:rgba(30,30,30,.9)}.avatar{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;background:#d68a34;color:#111;font-size:11px;font-weight:800}</style>
