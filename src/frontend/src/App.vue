<script setup lang="ts">
import { useRoute } from "vue-router";
import SidebarNav from "./components/SidebarNav.vue";
import TaskProgressToast from "./components/TaskProgressToast.vue";
import ShortcutsHelp from "./components/ShortcutsHelp.vue";
import CommandPalette from "./components/CommandPalette.vue";
import AppDialog from "./components/AppDialog.vue";
import { authChecked, currentUser, startupError } from "./state/auth";
import { loadSharedPreferences } from "./state/preferences";
import { watch } from "vue";

const route = useRoute();
// preferences are per user, so load them once someone is signed in
watch(
  () => currentUser.value?.id,
  (id) => {
    if (id) loadSharedPreferences();
  },
  { immediate: true },
);
const reloadApplication = () => window.location.reload();

const KEPT_ALIVE = [
  "MovieLibrary",
  "TVShowLibrary",
  "AnimeLibrary",
  "Calendar",
  "MediaLists",
  "Statistics",
  "Notifications",
];
</script>

<template>
  <main v-if="startupError" class="app-status app-failed">
    <div class="status-card">
      <div class="failure-icon" aria-hidden="true">×</div>
      <h1>Application failed</h1>
      <p>The application could not finish starting.</p>
      <button type="button" @click="reloadApplication">Reload application</button>
    </div>
  </main>
  <!-- First-run setup and the direct OIDC entrypoint deliberately bypass
       normal authentication, so both must render while authChecked is false. -->
  <template
    v-else-if="
      authChecked ||
      route.path === '/setup' ||
      route.path === '/login/oidcstart'
    "
  >
    <SidebarNav
      v-if="
        route.path !== '/login' &&
        route.path !== '/setup' &&
        route.path !== '/login/oidcstart'
      "
    />
    <!-- Library, calendar and list pages stay mounted when you leave them, so
         switching tabs is instant instead of reloading from empty. Detail
         pages are deliberately not kept: they must reload per title. -->
    <router-view v-slot="{ Component }">
      <KeepAlive :include="KEPT_ALIVE" :max="8">
        <component :is="Component" />
      </KeepAlive>
    </router-view>
    <TaskProgressToast
      v-if="route.path !== '/setup' && route.path !== '/login/oidcstart'"
    />
    <AppDialog />
    <ShortcutsHelp
      v-if="
        route.path !== '/login' &&
        route.path !== '/setup' &&
        route.path !== '/login/oidcstart'
      "
    />
    <CommandPalette
      v-if="
        route.path !== '/login' &&
        route.path !== '/setup' &&
        route.path !== '/login/oidcstart'
      "
    />
  </template>
  <main v-else class="app-status app-loading">
    <div class="status-card">
      <div class="loading-spinner" aria-hidden="true"></div>
      <p>Starting application…</p>
    </div>
  </main>
</template>

<style scoped>
.app-status {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #121212;
  color: #999;
  font-family: system-ui, sans-serif;
}

.status-card { display: flex; flex-direction: column; align-items: center; gap: 16px; text-align: center; }
.status-card h1 { margin: 0; color: #fff; font-size: 1.5rem; }
.status-card p { margin: 0; }
.loading-spinner { width: 44px; height: 44px; border: 4px solid #333; border-top-color: #aaa; border-radius: 50%; animation: spin 0.9s linear infinite; }
.failure-icon { width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; border: 4px solid #dc2626; border-radius: 50%; color: #ef4444; font-size: 42px; font-weight: 700; line-height: 1; }
.app-failed p { color: #aaa; }
.app-failed button { margin-top: 4px; border: 0; border-radius: 8px; padding: 10px 16px; background: #dc2626; color: #fff; font: inherit; font-weight: 600; cursor: pointer; }
.app-failed button:hover { background: #b91c1c; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
