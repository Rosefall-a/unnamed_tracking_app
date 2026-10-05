<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import { retryStartup } from "./router";
import SidebarNav from "./components/SidebarNav.vue";
import AppIcon from "./components/AppIcon.vue";
import TaskProgressToast from "./components/TaskProgressToast.vue";
import ShortcutsHelp from "./components/ShortcutsHelp.vue";
import CommandPalette from "./components/CommandPalette.vue";
import AppDialog from "./components/AppDialog.vue";
import AppearanceWelcome from "./components/AppearanceWelcome.vue";
import QuickTour from "./components/QuickTour.vue";
import { authChecked, currentUser } from "./state/auth";
import { mediaUnread } from "./state/notifications";
import { formatDocumentTitle, pageTitleOverride } from "./state/pageTitle";
import {
  preferences,
  preferencesLoaded,
  preferencesError,
  loadSharedPreferences,
  resetSharedPreferences,
} from "./state/preferences";
import {
  effectiveSidebarMode,
  sidebarWidth,
  sidebarResizing,
  navigationViewport,
  navigationMenuOpen,
  initializeNavigationViewport,
} from "./state/sidebarMode";
import { computed, watchEffect } from "vue";
import { startupError, startupState } from "./state/startup";

import { onUnmounted, watch } from "vue";
import {
  clearPluginExtensions,
  refreshPluginExtensions,
  pluginThemes,
} from "./state/pluginExtensions";
import { applyPluginThemeStyle } from "./services/pluginThemeStyle";
import PluginExtensionSlot from "./components/plugins/PluginExtensionSlot.vue";
import PluginOverlayHost from "./components/plugins/PluginOverlayHost.vue";
import { fetchCurrentUser } from "./services/auth";
import PwaStatus from "./components/PwaStatus.vue";

const route = useRoute();
const router = useRouter();
watchEffect(() => {
  applyPluginThemeStyle(
    document.documentElement,
    preferences.value.ui_palette,
    preferences.value.ui_custom_palette,
    pluginThemes.value,
  );
});
let startupRetryTimer: ReturnType<typeof setTimeout> | undefined;
watch(
  startupState,
  (state) => {
    clearTimeout(startupRetryTimer);
    if (state === "unavailable")
      startupRetryTimer = setTimeout(() => void retryStartup(), 5000);
  },
  { immediate: true },
);
const retryWhenOnline = () => {
  if (startupState.value === "unavailable") void retryStartup();
};
window.addEventListener("online", retryWhenOnline);
onUnmounted(() => {
  clearTimeout(startupRetryTimer);
  window.removeEventListener("online", retryWhenOnline);
});
const disposeNavigationViewport = initializeNavigationViewport();
onUnmounted(disposeNavigationViewport);
let pluginRefreshTimer: ReturnType<typeof setInterval> | undefined;
watch(
  () => currentUser.value?.id,
  (id) => {
    clearInterval(pluginRefreshTimer);
    clearPluginExtensions();
    if (id) {
      void refreshPluginExtensions();
      pluginRefreshTimer = setInterval(async () => {
        try {
          const user = await fetchCurrentUser();
          if (currentUser.value?.id !== id) return;
          if (!user) {
            currentUser.value = null;
            await router.replace("/login");
            return;
          }
          await refreshPluginExtensions();
        } catch {
          // Preserve the current screen during transient connectivity failures.
        }
      }, 5000);
    }
  },
  { immediate: true },
);
onUnmounted(() => {
  clearInterval(pluginRefreshTimer);
  clearPluginExtensions();
});
// "(2) Hades | Archive": the page (or what it shows) and unread notifications
watchEffect(() => {
  document.title = formatDocumentTitle(
    pageTitleOverride() ?? route.meta.title,
    currentUser.value ? mediaUnread.value : 0,
  );
});
// preferences are per user, so load them once someone is signed in
watch(
  () => currentUser.value?.id,
  (id) => {
    resetSharedPreferences();
    if (id) loadSharedPreferences();
  },
  { immediate: true, flush: "sync" },
);
const sidebarShown = computed(
  () => !route.path.startsWith("/login") && route.path !== "/setup",
);
// Pinned and rail modes sit in the page's own layout, so content needs to
// make room for them. Overlay floats above everything and reserves nothing.
// Pinned's reserved width tracks the sidebar's own (resizable) width;
// rail's collapsed width is fixed, since that's the "just icons" point.
const contentStyle = computed(() => {
  if (!sidebarShown.value) return {};
  if (effectiveSidebarMode.value === "pinned")
    return { marginLeft: `${sidebarWidth.value + 24}px` };
  if (effectiveSidebarMode.value === "rail") return { marginLeft: "88px" };
  return {};
});
const KEPT_ALIVE = [
  "GameLibrary",
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
  <PwaStatus />
  <!-- First-run setup and the direct OIDC entrypoint deliberately bypass
       normal authentication, so both must render while authChecked is false. -->
  <template
    v-if="
      (authChecked && startupState !== 'unavailable') ||
      route.path === '/setup' ||
      route.name === 'oidc-start' ||
      route.name === 'oidc-provider-start'
    "
  >
    <SidebarNav v-if="sidebarShown" />
    <header
      v-if="sidebarShown && navigationViewport === 'phone'"
      class="phone-topbar"
      aria-label="Page navigation"
    >
      <button
        type="button"
        aria-label="Open menu"
        aria-controls="app-navigation"
        data-tour="open-menu"
        :aria-expanded="navigationMenuOpen"
        @click="navigationMenuOpen = true"
      >
        <AppIcon name="menu" />
      </button>
      <span>{{ route.meta.title || "Library" }}</span>
    </header>
    <!-- Library, calendar and list pages stay mounted when you leave them, so
         switching tabs is instant instead of reloading from empty. Detail
         pages are deliberately not kept: they must reload per title. -->
    <div
      class="app-content"
      id="main-content"
      tabindex="-1"
      :class="{
        resizing: sidebarResizing,
        'phone-content': sidebarShown && navigationViewport === 'phone',
      }"
      :style="contentStyle"
    >
      <router-view v-slot="{ Component }">
        <KeepAlive :include="KEPT_ALIVE" :max="8" :key="currentUser?.id">
          <component :is="Component" />
        </KeepAlive>
      </router-view>
    </div>
    <PluginExtensionSlot
      v-if="currentUser"
      slot-id="app.global"
      :context="{ host_page: route.path }"
    />
    <PluginOverlayHost v-if="currentUser" />
    <TaskProgressToast v-if="sidebarShown" />
    <AppDialog />
    <ShortcutsHelp v-if="sidebarShown" />
    <CommandPalette v-if="sidebarShown" />
    <QuickTour v-if="sidebarShown" />
    <AppearanceWelcome
      v-if="
        sidebarShown &&
        currentUser &&
        preferencesLoaded &&
        !preferencesError &&
        !preferences.ui_welcome_completed
      "
      :key="currentUser.id"
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
      <p>Checking again automatically. You can retry now.</p>
      <button type="button" @click="retryStartup">Retry connection</button>
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
  color: var(--ui-text);
  margin: 0 0 12px;
}

.startup-error p {
  line-height: 1.5;
}

.startup-detail {
  color: var(--ui-error);
  font-size: 12px;
  word-break: break-word;
}

.startup-error button {
  margin-top: 8px;
  border: 0;
  border-radius: 8px;
  padding: 10px 16px;
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  font-weight: 700;
  cursor: pointer;
}

.app-loading {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ui-bg);
  color: var(--ui-dim);
  font-family: var(--ui-font-family);
}

.app-content {
  transition: margin-left 0.18s ease;
}

.app-content.resizing {
  transition: none;
}
.phone-content {
  padding-bottom: calc(92px + env(safe-area-inset-bottom));
}
.phone-topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 52px;
  padding: env(safe-area-inset-top) 16px 0;
  color: var(--ui-dim);
  background: var(--ui-bg);
  font-size: var(--ui-font-small);
}
.phone-topbar button {
  display: grid;
  place-items: center;
  min-width: 44px;
  min-height: 44px;
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-control);
  color: var(--ui-text);
  background: var(--ui-surface);
}
</style>
