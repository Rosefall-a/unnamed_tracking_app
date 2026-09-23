<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import SidebarNav from "./components/SidebarNav.vue";
import TaskProgressToast from "./components/TaskProgressToast.vue";
import ShortcutsHelp from "./components/ShortcutsHelp.vue";
import CommandPalette from "./components/CommandPalette.vue";
import { authChecked } from "./state/auth";
import { serverStartupPhase } from "./state/serverStartup";
const route = useRoute();
const startupMessage = computed(() => ({waiting_for_database:"Waiting for the database…",running_migrations:"Updating the database…",starting_api:"Starting the application server…",waiting_for_backend:"Starting the server…",ready:"Server ready"}[serverStartupPhase.value]));
const startupDetail = computed(() => ({waiting_for_database:"The backend is waiting for PostgreSQL to become ready.",running_migrations:"Applying database migrations and preparing your data.",starting_api:"The API is starting. This page will continue checking automatically.",waiting_for_backend:"The backend is starting. This page will continue checking automatically.",ready:"The backend is ready."}[serverStartupPhase.value]));
const startupStep = computed(() => ({waiting_for_backend:0,waiting_for_database:1,running_migrations:2,starting_api:3,ready:3}[serverStartupPhase.value]));
</script>
<template>
  <main v-if="!authChecked" class="app-loading" aria-live="polite"><section class="startup-card"><div class="brand-mark" aria-hidden="true">🎮</div><h1>Starting Archive</h1><p class="startup-message">{{ startupMessage }}</p><div class="spinner" aria-hidden="true"></div><p class="startup-detail">{{ startupDetail }}</p><ol class="startup-steps"><li :class="{active:startupStep===1,done:startupStep>1}">PostgreSQL</li><li :class="{active:startupStep===2,done:startupStep>2}">Database migrations</li><li :class="{active:startupStep===3}">Application server</li></ol></section></main>
  <template v-else><SidebarNav v-if="!['/login','/setup','/login/oidcstart'].includes(route.path)"/><router-view/><TaskProgressToast v-if="!['/setup','/login/oidcstart'].includes(route.path)"/><ShortcutsHelp v-if="!['/login','/setup','/login/oidcstart'].includes(route.path)"/><CommandPalette v-if="!['/login','/setup','/login/oidcstart'].includes(route.path)"/></template>
</template>
<style scoped>
.app-loading{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#121212;color:#fff;font-family:system-ui,sans-serif;padding:24px}.startup-card{width:min(460px,100%);padding:40px 36px;border:1px solid #2d2d2d;border-radius:16px;background:#1a1a1a;text-align:center}.brand-mark{font-size:38px}.startup-card h1{margin:0;font-size:1.45rem}.startup-message{margin:22px 0 14px;font-weight:600}.startup-detail{margin:14px auto 26px;max-width:380px;color:#929292;font-size:13px;line-height:1.55}.spinner{width:28px;height:28px;margin:0 auto;border:3px solid #333;border-top-color:#d68a34;border-radius:50%;animation:spin .85s linear infinite}.startup-steps{display:grid;gap:8px;margin:0;padding:0;list-style:none;text-align:left}.startup-steps li{padding:10px 12px;border-radius:8px;background:#151515;color:#686868;font-size:13px}.startup-steps li.active{color:#eee;background:#202020}.startup-steps li.done{color:#9c9c9c}@keyframes spin{to{transform:rotate(360deg)}}
</style>
