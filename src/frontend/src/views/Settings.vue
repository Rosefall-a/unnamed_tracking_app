<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
  defineAsyncComponent,
  type Component,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import { currentUser } from "../state/auth";
import { startTrackingSaves, stopTrackingSaves } from "../state/saveStatus";
import SettingsNav from "../components/settings/SettingsNav.vue";
import type { SettingsGroup } from "../components/settings/SettingsNav.vue";
import SettingsTabs from "../components/settings/SettingsTabs.vue";
import SaveStatus from "../components/settings/SaveStatus.vue";
import ProfileSection from "../components/settings/ProfileSection.vue";
import AccountChip from "../components/AccountChip.vue";
import SettingsSearch from "../components/settings/SettingsSearch.vue";
import BackButton from "../components/BackButton.vue";
import "../styles/settings.css";
import { fetchBackups, fetchProviderCredentials } from "../services/settings";
import {
  SETTINGS_PAGES,
  resolveSettingsPlace,
  visiblePages,
  visibleTabs,
  type SettingsPart,
} from "../utils/settingsPages";

// only the open tab's sections are downloaded
const lazy = (load: () => Promise<{ default: Component }>) =>
  defineAsyncComponent(load);
const PARTS: Record<SettingsPart, { is: Component; props?: object }> = {
  profile: { is: ProfileSection },
  connections: {
    is: lazy(() => import("../components/settings/ConnectionsSection.vue")),
  },
  anilist: {
    is: lazy(() => import("../components/settings/AniListImportSection.vue")),
  },
  "api-keys": {
    is: lazy(() => import("../components/settings/ApiKeysSection.vue")),
  },
  devices: {
    is: lazy(() => import("../components/settings/DevicesSection.vue")),
  },
  appearance: {
    is: lazy(() => import("../components/settings/AppearanceSection.vue")),
    props: { part: "colors" },
  },
  display: {
    is: lazy(() => import("../components/settings/InterfaceSection.vue")),
    props: { part: "display" },
  },
  "appearance-badge": {
    is: lazy(() => import("../components/settings/AppearanceSection.vue")),
    props: { part: "badge" },
  },
  interface: {
    is: lazy(() => import("../components/settings/InterfaceSection.vue")),
  },
  sidebar: {
    is: lazy(() => import("../components/settings/SidebarSettingsSection.vue")),
  },
  "add-defaults": {
    is: lazy(() => import("../components/settings/AddDefaultsSection.vue")),
  },
  "media-prefs": {
    is: lazy(
      () => import("../components/settings/MediaPreferencesSection.vue"),
    ),
  },
  "game-page": {
    is: lazy(() => import("../components/settings/GamePageSection.vue")),
  },
  shortcuts: {
    is: lazy(
      () => import("../components/settings/KeyboardShortcutsSection.vue"),
    ),
  },
  notifications: {
    is: lazy(
      () => import("../components/settings/CalendarNotificationsSection.vue"),
    ),
    props: { part: "notifications" },
  },
  calendar: {
    is: lazy(
      () => import("../components/settings/CalendarNotificationsSection.vue"),
    ),
    props: { part: "calendar" },
  },
  upload: {
    is: lazy(() => import("../components/settings/UploadSection.vue")),
  },
  duplicates: {
    is: lazy(() => import("../components/settings/DuplicateGamesSection.vue")),
  },
  "library-folders": {
    is: lazy(
      () => import("../components/settings/LibraryManagementSection.vue"),
    ),
    props: { part: "folders" },
  },
  "library-refresh": {
    is: lazy(
      () => import("../components/settings/LibraryManagementSection.vue"),
    ),
    props: { part: "refresh" },
  },
  "media-trash": {
    is: lazy(() => import("../components/settings/MediaTrashSection.vue")),
  },
  export: {
    is: lazy(() => import("../components/settings/ExportImportSection.vue")),
  },
  "metadata-sources": {
    is: lazy(() => import("../components/settings/MetadataSourcesSection.vue")),
  },
  scan: {
    is: lazy(() => import("../components/settings/ScanSettingsSection.vue")),
  },
  "steam-tags": {
    is: lazy(() => import("../components/settings/SteamTagsSection.vue")),
  },
  "steam-wishlist": {
    is: lazy(() => import("../components/settings/SteamWishlistSection.vue")),
  },
  "media-refresh": {
    is: lazy(() => import("../components/settings/MediaRefreshSection.vue")),
  },
  "server-overview": {
    is: lazy(() => import("../components/settings/ServerOverviewSection.vue")),
  },
  stats: {
    is: lazy(() => import("../components/settings/StatsSection.vue")),
  },
  users: {
    is: lazy(() => import("../components/settings/AdminSection.vue")),
  },
  tasks: {
    is: lazy(() => import("../components/settings/TasksSection.vue")),
  },
  backups: {
    is: lazy(() => import("../components/settings/BackupsSection.vue")),
  },
  repair: {
    is: lazy(() => import("../components/settings/RepairSection.vue")),
  },
  oidc: {
    is: lazy(() => import("../components/settings/OidcSettingsSection.vue")),
  },
  "server-integrations": {
    is: lazy(
      () => import("../components/settings/ServerIntegrationsSection.vue"),
    ),
  },
  limits: {
    is: lazy(() => import("../components/settings/LimitsSection.vue")),
  },
  "password-policy": {
    is: lazy(() => import("../components/settings/PasswordPolicySection.vue")),
  },
  "dev-tools": {
    is: lazy(() => import("../components/settings/DevToolsSection.vue")),
  },
  logs: {
    is: lazy(() => import("../components/settings/ComingSoonSection.vue")),
    props: {
      title: "Logs",
      description:
        "An audit trail of edits made across the library, including changes made by other users.",
      plannedFeatures: [
        "Who changed what, and when",
        "Filter by user, game, or field",
        "Restore a previous value",
      ],
    },
  },
};

const router = useRouter();
const route = useRoute();
function goBack() {
  if (window.history.length > 1) router.back();
  else router.push("/");
}

onMounted(startTrackingSaves);
onBeforeUnmount(stopTrackingSaves);

const isAdmin = computed(() => !!currentUser.value?.is_admin);

// Things that need a look, counted on the tab that fixes them and on its page
// in the menu: a missing TMDB key (new shows get no art or seasons), and for
// admins, backups that would be lost with the data or are switched off.
const warnings = ref<Record<string, number>>({});
onMounted(async () => {
  const found: Record<string, number> = {};
  try {
    const creds = await fetchProviderCredentials();
    const tmdb = creds.TMDB;
    if (tmdb && tmdb.status === "not_configured" && !tmdb.server_configured)
      found["sources:providers"] = 1;
  } catch {
    // no badge is better than a wrong one
  }
  if (isAdmin.value) {
    try {
      const b = await fetchBackups();
      const n =
        Number(!b.enabled) +
        Number(!!b.storage.sameDrive) +
        Number(!!b.storage.backups && !b.storage.backups.mounted);
      if (n) {
        found["server:overview"] = n;
        found["server:tasks"] = n;
      }
    } catch {
      // as above
    }
  }
  warnings.value = found;
});
function pageWarnings(pageId: string): number {
  const page = SETTINGS_PAGES.find((p) => p.id === pageId);
  if (!page) return 0;
  // the overview repeats the tasks count, so count each problem once
  if (pageId === "server") return warnings.value["server:tasks"] ?? 0;
  return page.tabs.reduce(
    (n, t) => n + (warnings.value[`${pageId}:${t.id}`] ?? 0),
    0,
  );
}

const groups = computed<SettingsGroup[]>(() => {
  const out: SettingsGroup[] = [];
  for (const page of visiblePages(isAdmin.value)) {
    let group = out.find((g) => g.label === page.group);
    if (!group) {
      group = { label: page.group, sections: [] };
      out.push(group);
    }
    group.sections.push({
      id: page.id,
      label: page.label,
      sub: page.sub,
      badge: pageWarnings(page.id),
    });
  }
  return out;
});

function queryString(key: string): string | undefined {
  const v = route.query[key];
  return typeof v === "string" && v ? v : undefined;
}

const place = computed(() =>
  resolveSettingsPlace(
    queryString("section"),
    queryString("tab"),
    isAdmin.value,
  ),
);
const page = computed(() =>
  SETTINGS_PAGES.find((p) => p.id === place.value.section)!,
);
const tabs = computed(() => visibleTabs(page.value, isAdmin.value));
const tab = computed(() => tabs.value.find((t) => t.id === place.value.tab)!);

// keep the address bar on the real page and tab, so a refresh, a bookmark or
// an old link all settle on the same place
watch(
  place,
  (p) => {
    if (queryString("section") === p.section && queryString("tab") === p.tab)
      return;
    void router.replace({
      query: { ...route.query, section: p.section, tab: p.tab },
    });
  },
  { immediate: true },
);

function openPage(id: string) {
  const p = resolveSettingsPlace(id, undefined, isAdmin.value);
  void router.replace({
    query: { ...route.query, section: p.section, tab: p.tab },
  });
}
function openTab(id: string) {
  void router.replace({
    query: { ...route.query, section: place.value.section, tab: id },
  });
}
function openFromSearch(target: { section: string; tab: string }) {
  void router.replace({
    query: { ...route.query, section: target.section, tab: target.tab },
  });
}

const card = ref<HTMLElement | null>(null);
watch(
  () => place.value.section,
  async () => {
    if (!window.matchMedia("(max-width: 760px)").matches) return;
    await nextTick();
    card.value?.scrollIntoView({ behavior: "smooth", block: "start" });
  },
);
</script>

<template>
  <main class="settings-page">
    <BackButton fixed @click="goBack" />
    <AccountChip fixed />
    <div class="settings-layout">
      <div class="settings-head">
        <h1>Settings</h1>
        <SettingsSearch :is-admin="isAdmin" @select="openFromSearch" />
        <SaveStatus />
      </div>
      <div class="settings-body">
        <SettingsNav
          :active-section="place.section"
          :groups="groups"
          @update:active-section="openPage"
        />
        <div ref="card" class="settings-card">
          <div class="page-head">
            <h2>{{ page.label }}</h2>
            <p class="page-lead">{{ page.lead }}</p>
          </div>
          <SettingsTabs
            v-if="tabs.length > 1"
            :model-value="place.tab"
            :tabs="
              tabs.map((t) => ({
                ...t,
                badge: warnings[`${place.section}:${t.id}`] ?? 0,
              }))
            "
            @update:model-value="openTab"
          />
          <div
            :key="place.section + ':' + place.tab"
            class="tab-parts st-cards"
          >
            <component
              :is="PARTS[part].is"
              v-for="part in tab.parts"
              :key="part"
              v-bind="PARTS[part].props"
            />
          </div>
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.settings-page {
  position: relative;
  min-height: 100vh;
  padding: 84px 40px 40px;
  background: var(--ui-bg);
  font-family: system-ui, sans-serif;
}
.settings-layout {
  width: 100%;
  color: var(--ui-heading);
}
.settings-head {
  max-width: 1140px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px 16px;
  margin: 0 auto 24px;
}
.settings-head h1 {
  margin-right: auto;
}
.settings-layout h1 {
  margin: 0;
  font-size: 1.7rem;
  font-weight: 800;
}
.settings-body {
  display: flex;
  gap: 32px;
  align-items: flex-start;
  max-width: 1140px;
  margin: 0 auto;
}
.settings-card {
  flex: 999 1 560px;
  min-width: 0;
  scroll-margin-top: 64px;
}
.page-head h2 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 750;
  color: var(--ui-heading);
}
.page-lead {
  margin: 4px 0 14px;
  color: var(--ui-dim);
  font-size: 13.5px;
}

@media (max-width: 760px) {
  .settings-body {
    flex-direction: column;
  }
  .settings-card {
    width: 100%;
    /* at least a screen tall, so there is always room to scroll a section to
       the top while its content is still loading (a short card left the page
       too short to scroll that far, and the section half off-screen) */
    min-height: calc(100vh - 64px);
    box-sizing: border-box;
  }
}
</style>
