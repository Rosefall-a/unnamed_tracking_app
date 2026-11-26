<script setup lang="ts">
import { useRoute } from "vue-router";
import SidebarNav from "./components/SidebarNav.vue";
import NavAlternate from "./components/NavAlternate.vue";
import { sidebarStyle } from "./state/sidebarPrefs";
import { usesSideNav } from "./state/navData";
import TaskProgressToast from "./components/TaskProgressToast.vue";
import ShortcutsHelp from "./components/ShortcutsHelp.vue";
import CommandPalette from "./components/CommandPalette.vue";
import AppDialog from "./components/AppDialog.vue";
import CompletionToast from "./components/CompletionToast.vue";
import { authChecked, currentUser } from "./state/auth";
import { mediaUnread, refreshMediaNotifications } from "./state/notifications";
import { formatDocumentTitle, pageTitleOverride } from "./state/pageTitle";
import { loadSharedPreferences, preferences } from "./state/preferences";
import { applySavedThemeColors } from "./state/themeColors";
import {
  sidebarMode,
  sidebarWidth,
  sidebarResizing,
} from "./state/sidebarMode";
import { computed, ref, watch, watchEffect } from "vue";
import { startupError, startupState } from "./state/startup";
import { useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
// Until the first navigation (and any redirect, such as to the login screen)
// has finished, the route is still the empty start location; drawing the app
// then flashes the home page's chrome before the login screen replaces it.
const routerReady = ref(false);
router
  .isReady()
  .then(() => {
    routerReady.value = true;
  })
  .catch(() => {
    /* an aborted first navigation shows the startup screens below instead */
  });
// "(2) Hades | Archive": the page (or what it shows) and unread notifications
watchEffect(() => {
  document.title = formatDocumentTitle(
    pageTitleOverride() ?? route.meta.title,
    currentUser.value ? mediaUnread.value : 0,
  );
});
// Asking the server for notifications is also what makes it create the newly
// due ones, so this check is the whole "delivery": every 5 minutes while the
// app is open and someone is signed in, nothing running otherwise. It lives
// here, not in a sidebar, so every navigation style gets it.
let notificationTimer: number | undefined;
watch(
  () => currentUser.value?.id ?? null,
  (id) => {
    window.clearInterval(notificationTimer);
    if (!id) return;
    void refreshMediaNotifications({ maxAgeMs: 30_000 });
    notificationTimer = window.setInterval(
      () => void refreshMediaNotifications(),
      5 * 60 * 1000,
    );
  },
  { immediate: true },
);
// preferences are per user, so load them once someone is signed in
watch(
  () => currentUser.value?.id,
  (id) => {
    if (id) loadSharedPreferences();
  },
  { immediate: true },
);
// Lists, Home's data and other caches live in memory for the whole visit, and
// signing out and in does not reload the page. When a different account signs
// in, start over so nothing of the last account's library is shown.
let lastSignedIn: string | null = null;
watch(
  () => currentUser.value?.id ?? null,
  (id) => {
    if (!id) return;
    if (lastSignedIn && lastSignedIn !== id) window.location.reload();
    lastSignedIn = id;
  },
  { immediate: true },
);
// saved colours replace the cached ones once preferences arrive, and follow changes
watch(() => preferences.value.theme_colors, applySavedThemeColors, {
  deep: true,
});
const sidebarShown = computed(
  () =>
    route.path !== "/login" &&
    route.path !== "/setup" &&
    route.path !== "/login/oidcstart",
);
// Pinned and rail modes sit in the page's own layout, so content needs to
// make room for them. Overlay floats above everything and reserves nothing.
// Pinned's reserved width tracks the sidebar's own (resizable) width;
// rail's collapsed width is fixed, since that's the "just icons" point.
const sideNav = computed(() => usesSideNav(sidebarStyle.value));
const contentStyle = computed(() => {
  if (!sidebarShown.value) return {};
  // the styles without a sidebar keep room only for what stays on screen
  if (sidebarStyle.value === "topbar") return { paddingTop: "56px" };
  if (sidebarStyle.value === "dock") return { paddingBottom: "84px" };
  if (sidebarStyle.value === "guide" || sidebarStyle.value === "peek")
    return {};
  // rail and panel: styles/nav.css keeps room for it, narrower on a phone
  if (sidebarStyle.value === "railpanel") return {};
  if (sidebarMode.value === "pinned")
    return { marginLeft: `${sidebarWidth.value}px` };
  if (sidebarMode.value === "rail") return { marginLeft: "56px" };
  return {};
});
// Pages read the navigation style off <html> (styles/nav.css): the top bar
// replaces their account chip and must not have their header slide under it.
watchEffect(() => {
  const root = document.documentElement;
  if (sidebarShown.value) root.dataset.nav = sidebarStyle.value;
  else delete root.dataset.nav;
});
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
  <!-- First-run setup and the direct OIDC entrypoint deliberately bypass
       normal authentication, so both must render while authChecked is false. -->
  <template
    v-if="
      (authChecked && routerReady) ||
      route.path === '/setup' ||
      route.path === '/login/oidcstart'
    "
  >
    <SidebarNav v-if="sidebarShown && sideNav" />
    <NavAlternate v-else-if="sidebarShown" />
    <!-- Library, calendar and list pages stay mounted when you leave them, so
         switching tabs is instant instead of reloading from empty. Detail
         pages are deliberately not kept: they must reload per title. -->
    <div
      class="app-content"
      :class="{ resizing: sidebarResizing }"
      :style="contentStyle"
    >
      <router-view v-slot="{ Component }">
        <KeepAlive :include="KEPT_ALIVE" :max="8">
          <component :is="Component" />
        </KeepAlive>
      </router-view>
    </div>
    <TaskProgressToast
      v-if="route.path !== '/setup' && route.path !== '/login/oidcstart'"
    />
    <AppDialog />
    <CompletionToast v-if="currentUser && sidebarShown" />
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
  <main v-else-if="startupState === 'unavailable'" class="app-loading">
    <section class="startup-error">
      <h1>Backend unavailable</h1>
      <p>
        The frontend cannot reach the backend yet. It may still be starting or
        may be temporarily unavailable.
      </p>
      <p v-if="startupError" class="startup-detail">{{ startupError }}</p>
      <button type="button" @click="router.go(0)">Retry</button>
    </section>
  </main>
  <main v-else class="app-loading">
    <p>Loading…</p>
  </main>
</template>

<style scoped>
.startup-error {
  max-width: 520px;
  padding: 32px;
  text-align: center;
  border: 1px solid var(--ui-border);
  border-radius: 14px;
  background: var(--ui-surface);
}

.startup-error h1 {
  color: var(--ui-heading);
  margin: 0 0 12px;
}

.startup-error p {
  line-height: 1.5;
}

.startup-detail {
  color: var(--ui-error-text);
  font-size: 12px;
  word-break: break-word;
}

.startup-error button {
  margin-top: 8px;
  border: 0;
  border-radius: 8px;
  padding: 10px 16px;
  background: var(--ui-accent);
  color: #111;
  font-weight: 700;
  cursor: pointer;
}

.app-loading {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ui-bg);
  color: var(--ui-dim-3);
  font-family: system-ui, sans-serif;
}

.app-content {
  transition: margin-left 0.18s ease;
}

.app-content.resizing {
  transition: none;
}
</style>
