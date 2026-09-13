<script setup lang="ts">
import { useRoute } from "vue-router";
import SidebarNav from "./components/SidebarNav.vue";
import ProfileDock from "./components/ProfileDock.vue";
import TaskProgressToast from "./components/TaskProgressToast.vue";
import ShortcutsHelp from "./components/ShortcutsHelp.vue";
import CommandPalette from "./components/CommandPalette.vue";
import { authChecked } from "./state/auth";

const route = useRoute();

const isPublicRoute = () =>
  route.path === "/login" ||
  route.path === "/setup" ||
  route.path === "/login/oidcstart" ||
  route.path === "/reset-password";
</script>

<template>
  <template
    v-if="
      authChecked ||
      route.path === '/setup' ||
      route.path === '/login/oidcstart' ||
      route.path === '/reset-password'
    "
  >
    <SidebarNav v-if="!isPublicRoute()" />
    <router-view />
    <ProfileDock v-if="!isPublicRoute()" />
    <TaskProgressToast v-if="!isPublicRoute()" />
    <ShortcutsHelp v-if="!isPublicRoute()" />
    <CommandPalette v-if="!isPublicRoute()" />
  </template>

  <main v-else class="app-loading">
    <p>Loading…</p>
  </main>
</template>

<style scoped>
.app-loading {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #121212;
  color: #999;
  font-family: system-ui, sans-serif;
}
</style>
