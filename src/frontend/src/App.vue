<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import SidebarNav from "./components/SidebarNav.vue";
import DesktopSidebar from "./components/DesktopSidebar.vue";
import ProfileChip from "./components/ProfileChip.vue";
import NotificationBell from "./components/NotificationBell.vue";
import TaskProgressToast from "./components/TaskProgressToast.vue";
import ShortcutsHelp from "./components/ShortcutsHelp.vue";
import CommandPalette from "./components/CommandPalette.vue";
import { authChecked } from "./state/auth";
import { serverStartupPhase } from "./state/serverStartup";

const route = useRoute();

const isPublicRoute = () =>
  route.path === "/login" ||
  route.path === "/setup" ||
  route.path === "/login/oidcstart" ||
  route.path === "/reset-password";

const startupMessage = computed(() => {
  switch (serverStartupPhase.value) {
    case "waiting_for_database":
      return "Waiting for the database…";
    case "running_migrations":
      return "Updating the database…";
    case "starting_api":
      return "Starting the application server…";
    case "ready":
      return "Server ready";
    default:
      return "Starting the server…";
  }
});

const startupDetail = computed(() => {
  switch (serverStartupPhase.value) {
    case "waiting_for_database":
      return "The backend is waiting for PostgreSQL to become ready.";
    case "running_migrations":
      return "Applying database migrations and preparing your data.";
    case "starting_api":
      return "Almost there. The API is starting and the application will load automatically.";
    default:
      return "The backend is starting. This page will continue checking automatically.";
  }
});

const startupStep = computed(() => {
  switch (serverStartupPhase.value) {
    case "waiting_for_database": return 1;
    case "running_migrations": return 2;
    case "starting_api": return 3;
    default: return 0;
  }
});
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
    <template v-if="!isPublicRoute()">
      <SidebarNav />
      <DesktopSidebar />
    </template>
    <router-view />
    <NotificationBell v-if="!isPublicRoute()" />
    <ProfileChip v-if="!isPublicRoute()" />
    <TaskProgressToast v-if="!isPublicRoute()" />
    <ShortcutsHelp v-if="!isPublicRoute()" />
    <CommandPalette v-if="!isPublicRoute()" />
  </template>

  <main v-else class="app-loading">
    <section class="startup-card" aria-live="polite">
      <div class="brand-mark" aria-hidden="true">🎮</div>
      <h1>Starting Archive</h1>
      <p class="startup-message">{{ startupMessage }}</p>
      <div class="spinner" aria-hidden="true"></div>
      <p class="startup-detail">{{ startupDetail }}</p>

      <ol class="startup-steps">
        <li :class="{ active: startupStep === 1, done: startupStep > 1 }">PostgreSQL</li>
        <li :class="{ active: startupStep === 2, done: startupStep > 2 }">Database migrations</li>
        <li :class="{ active: startupStep === 3 }">Application server</li>
      </ol>
    </section>
  </main>
</template>

<style scoped>
.app-loading {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #121212;
  color: #fff;
  font-family: system-ui, sans-serif;
  padding: 24px;
}

.startup-card {
  width: min(460px, 100%);
  padding: 40px 36px;
  border: 1px solid #2d2d2d;
  border-radius: 16px;
  background: #1a1a1a;
  text-align: center;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
}

.brand-mark {
  font-size: 38px;
  margin-bottom: 10px;
}

.startup-card h1 {
  margin: 0;
  font-size: 1.45rem;
}

.startup-message {
  margin: 22px 0 14px;
  color: #e6e6e6;
  font-size: 1rem;
  font-weight: 600;
}

.startup-detail {
  margin: 14px auto 26px;
  max-width: 380px;
  color: #929292;
  font-size: 13px;
  line-height: 1.55;
}

.spinner {
  width: 28px;
  height: 28px;
  margin: 0 auto;
  border: 3px solid #333;
  border-top-color: #d68a34;
  border-radius: 50%;
  animation: spin 0.85s linear infinite;
}

.startup-steps {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
  text-align: left;
}

.startup-steps li {
  position: relative;
  padding: 10px 12px 10px 34px;
  border-radius: 8px;
  background: #151515;
  color: #686868;
  font-size: 13px;
  transition: color 0.2s, background 0.2s;
}

.startup-steps li::before {
  content: "";
  position: absolute;
  left: 12px;
  top: 50%;
  width: 8px;
  height: 8px;
  border: 2px solid #555;
  border-radius: 50%;
  transform: translateY(-50%);
}

.startup-steps li.active {
  color: #eee;
  background: #202020;
}

.startup-steps li.active::before {
  border-color: #d68a34;
  box-shadow: 0 0 0 3px rgba(214, 138, 52, 0.12);
}

.startup-steps li.done {
  color: #9c9c9c;
}

.startup-steps li.done::before {
  border-color: #6f9d78;
  background: #6f9d78;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
