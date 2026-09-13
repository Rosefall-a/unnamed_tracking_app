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
  <!-- First-run setup deliberately bypasses normal authentication, so it must
       render even though authChecked remains false until an account exists. -->
  <template v-if="authChecked || route.path === '/setup'">
    <SidebarNav v-if="route.path !== '/login' && route.path !== '/setup'" />
    <router-view />
    <TaskProgressToast v-if="route.path !== '/setup'" />
    <ShortcutsHelp v-if="route.path !== '/login' && route.path !== '/setup'" />
    <CommandPalette v-if="route.path !== '/login' && route.path !== '/setup'" />
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
