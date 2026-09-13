<script setup lang="ts">
import { useRoute } from "vue-router";
import SidebarNav from "./components/SidebarNav.vue";
import TaskProgressToast from "./components/TaskProgressToast.vue";
import ShortcutsHelp from "./components/ShortcutsHelp.vue";
import CommandPalette from "./components/CommandPalette.vue";
import { authChecked } from "./state/auth";

const route = useRoute();
</script>

<template>
  <!-- First-run setup and the direct OIDC entrypoint deliberately bypass
       normal authentication, so both must render while authChecked is false. -->
  <template v-if="authChecked || route.path === '/setup' || route.path === '/login/oidcstart'">
    <SidebarNav v-if="route.path !== '/login' && route.path !== '/setup' && route.path !== '/login/oidcstart'" />
    <router-view />
    <TaskProgressToast v-if="route.path !== '/setup' && route.path !== '/login/oidcstart'" />
    <ShortcutsHelp v-if="route.path !== '/login' && route.path !== '/setup' && route.path !== '/login/oidcstart'" />
    <CommandPalette v-if="route.path !== '/login' && route.path !== '/setup' && route.path !== '/login/oidcstart'" />
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
