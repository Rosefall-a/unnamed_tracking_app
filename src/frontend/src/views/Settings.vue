<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import { currentUser } from "../state/auth";
import { startTrackingSaves, stopTrackingSaves } from "../state/saveStatus";
import SettingsNav from "../components/settings/SettingsNav.vue";
import type { SettingsGroup } from "../components/settings/SettingsNav.vue";
import SaveStatus from "../components/settings/SaveStatus.vue";
import ProfileSection from "../components/settings/ProfileSection.vue";
import InterfaceSection from "../components/settings/InterfaceSection.vue";
import AppearanceSection from "../components/settings/AppearanceSection.vue";
import BrandingSection from "../components/settings/BrandingSection.vue";
import UploadSection from "../components/settings/UploadSection.vue";
import LibrarySettings from "../components/settings/LibrarySettings.vue";
import MetadataSettings from "../components/settings/MetadataSettings.vue";
import AdminSettings from "../components/settings/AdminSettings.vue";
import TasksSection from "../components/settings/TasksSection.vue";
import StatsSection from "../components/settings/StatsSection.vue";
import ExportImportSection from "../components/settings/ExportImportSection.vue";
import CalendarNotificationsSection from "../components/settings/CalendarNotificationsSection.vue";
import KeyboardShortcutsSection from "../components/settings/KeyboardShortcutsSection.vue";
import ConnectionsSection from "../components/settings/ConnectionsSection.vue";
import AniListImportSection from "../components/settings/AniListImportSection.vue";
import ApiKeysSection from "../components/settings/ApiKeysSection.vue";
import PluginManagerSection from "../components/settings/PluginManagerSection.vue";
import PluginContributionHost from "../components/plugins/PluginContributionHost.vue";
import {
  pluginSettingsSections,
  pluginNavigation,
  pageReplacement,
  pageReplacementConflicts,
  refreshPluginExtensions,
} from "../state/pluginExtensions";
import AccountChip from "../components/AccountChip.vue";
import PageHeader from "../components/PageHeader.vue";
import AppIcon from "../components/AppIcon.vue";
import { usePageTitle } from "../state/pageTitle";

const router = useRouter();
const route = useRoute();
onMounted(() => void refreshPluginExtensions());

const coreSectionIds = new Set([
  "admin",
  "metadata",
  "connections",
  "notifications",
  "calendar",
  "shortcuts",
  "profile",
  "interface",
  "appearance",
  "branding",
  "api-keys",
  "calendar-notifications",
  "upload",
  "library",
  "media-prefs",
  "media-trash",
  "scan",
  "sources",
  "media-refresh",
  "export",
  "oidc",
  "server-integrations",
  "users",
  "plugins",
  "stats",
  "tasks",
  "logs",
]);
const visiblePluginSettings = computed(() => {
  const seen = new Set<string>();
  return pluginSettingsSections.value.filter((item) => {
    if (item.adminOnly && !currentUser.value?.is_admin) return false;
    if (
      coreSectionIds.has(item.contributionId) ||
      seen.has(item.contributionId)
    )
      return false;
    seen.add(item.contributionId);
    return true;
  });
});

function pluginSettingsId(contributionId: string): string {
  return contributionId;
}

const settingsReplacement = computed(() => pageReplacement("settings"));
const settingsReplacementConflicts = computed(() =>
  pageReplacementConflicts("settings"),
);
const showHostSettings = computed(
  () => currentUser.value?.is_admin && route.query.host === "1",
);

const activePluginSettings = computed(() =>
  visiblePluginSettings.value.find(
    (item) => pluginSettingsId(item.contributionId) === activeSection.value,
  ),
);
const visiblePluginSettingsNavigation = computed(() => {
  const seen = new Set(
    visiblePluginSettings.value.map((item) => item.contributionId),
  );
  return pluginNavigation.value.filter((item) => {
    if (item.location !== "settings.sidebar" || !item.pageId) return false;
    if (item.adminOnly && !currentUser.value?.is_admin) return false;
    if (
      coreSectionIds.has(item.contributionId) ||
      seen.has(item.contributionId)
    )
      return false;
    seen.add(item.contributionId);
    return true;
  });
});
const activePluginSettingsNavigation = computed(() =>
  visiblePluginSettingsNavigation.value.find(
    (item) => item.contributionId === activeSection.value,
  ),
);

onMounted(startTrackingSaves);
onBeforeUnmount(stopTrackingSaves);

const groups = computed<SettingsGroup[]>(() => {
  const result: SettingsGroup[] = [
    {
      label: "Account",
      area: "account",
      sections: [
        { id: "profile", label: "Profile" },
        { id: "connections", label: "Connections" },
        { id: "api-keys", label: "API Keys" },
      ],
    },
    {
      label: "Preferences",
      area: "preferences",
      sections: [
        { id: "interface", label: "User Interface" },
        { id: "appearance", label: "Appearance" },
        { id: "notifications", label: "Notifications" },
        { id: "calendar", label: "Calendar" },
        { id: "shortcuts", label: "Keyboard Shortcuts" },
      ],
    },
    {
      label: "Library",
      area: "preferences",
      sections: [
        { id: "upload", label: "Upload" },
        { id: "library", label: "Library" },
        { id: "metadata", label: "Metadata" },
        { id: "export", label: "Export / Import" },
      ],
    },
  ];
  if (currentUser.value?.is_admin)
    result.push({
      label: "Server management",
      area: "administration",
      sections: [
        { id: "admin", label: "Users & server configuration" },
        { id: "branding", label: "App branding" },
        { id: "plugins", label: "Plugins" },
        { id: "tasks", label: "Background tasks" },
        { id: "stats", label: "Storage & usage" },
      ],
    });
  else
    result.push({
      label: "Information",
      area: "preferences",
      sections: [{ id: "stats", label: "Storage & usage" }],
    });
  if (
    visiblePluginSettings.value.length ||
    visiblePluginSettingsNavigation.value.length
  ) {
    for (const adminOnly of [false, true]) {
      const sections = [
        ...visiblePluginSettings.value.map((item) => ({
          id: pluginSettingsId(item.contributionId),
          label: item.label,
          adminOnly: Boolean(item.adminOnly),
        })),
        ...visiblePluginSettingsNavigation.value.map((item) => ({
          id: item.contributionId,
          label: item.label,
          adminOnly: Boolean(item.adminOnly),
        })),
      ].filter((item) => item.adminOnly === adminOnly);
      if (sections.length)
        result.push({
          label: "Extensions",
          area: adminOnly ? "administration" : "preferences",
          sections,
        });
    }
  }
  return result;
});

// Sections that used to be their own entries and now live inside a
// merged page as a tab, so old links (command palette, bookmarks) still
// land in the right place.
const SECTION_ALIASES: Record<string, { section: string; tab?: string }> = {
  "calendar-notifications": { section: "notifications" },
  "media-prefs": { section: "library", tab: "preferences" },
  "media-trash": { section: "library", tab: "trash" },
  sources: { section: "metadata", tab: "sources" },
  scan: { section: "metadata", tab: "scan" },
  "media-refresh": { section: "metadata", tab: "refresh" },
  users: { section: "admin", tab: "users" },
  oidc: { section: "admin", tab: "sso" },
  "server-integrations": { section: "admin", tab: "integrations" },
};
function resolveSection(id: string | undefined): {
  section: string;
  tab?: string;
} {
  const raw = id || "";
  return SECTION_ALIASES[raw] ?? { section: raw };
}
const initial = resolveSection(route.query.section as string | undefined);
const activeSection = ref(initial.section);
const initialTab = ref<string | undefined>(
  (route.query.tab as string | undefined) ?? initial.tab,
);
function openSection(id: string) {
  const r = resolveSection(id);
  initialTab.value = r.tab;
  activeSection.value = r.section;
}

watch(
  () => route.query.section,
  (section) => {
    const next = resolveSection(
      typeof section === "string" ? section : undefined,
    );
    initialTab.value = (route.query.tab as string | undefined) ?? next.tab;
    if (activeSection.value !== next.section)
      activeSection.value = next.section;
  },
);

watch(activeSection, (section) => {
  const current =
    typeof route.query.section === "string" ? route.query.section : "";
  if (current === section) return;
  void router.replace({ query: { ...route.query, section } });
});

const card = ref<HTMLElement | null>(null);
watch(activeSection, async () => {
  if (!window.matchMedia("(max-width: 760px)").matches) return;
  await nextTick();
  card.value?.focus({ preventScroll: true });
  card.value?.scrollIntoView({ behavior: "instant", block: "start" });
});

const selectedGroup = computed(() =>
  groups.value.find((group) =>
    group.sections.some((section) => section.id === activeSection.value),
  ),
);
const selectedSection = computed(() =>
  selectedGroup.value?.sections.find(
    (section) => section.id === activeSection.value,
  ),
);
const area = computed(() => {
  if (selectedGroup.value) return selectedGroup.value.area;
  if (route.query.area === "account") return "account";
  if (route.query.area === "administration" && currentUser.value?.is_admin)
    return "administration";
  return "preferences";
});
const areaNames = {
  preferences: "Preferences",
  account: "Account",
  administration: "Administration",
};
const areaDescriptions = {
  preferences: "Make your library feel like yours.",
  account: "Your profile, security and connected services.",
  administration: "Server-wide settings affect everyone on this instance.",
};
const areaGroups = computed(() =>
  groups.value.filter((group) => group.area === area.value),
);
const sectionTitle = computed(
  () => selectedSection.value?.label ?? areaNames[area.value],
);
usePageTitle(() => sectionTitle.value);
function openArea(next: string) {
  void router.push({
    path: "/settings",
    query: { area: next, ...(showHostSettings.value ? { host: "1" } : {}) },
  });
}
function backToArea() {
  openArea(area.value);
}
</script>

<template>
  <main
    v-if="settingsReplacement && !showHostSettings"
    class="settings-page plugin-settings-replacement"
  >
    <p v-if="currentUser?.is_admin" class="replacement-notice" role="status">
      <template v-if="settingsReplacementConflicts.length > 1">
        Multiple plugins requested Settings replacement. The deterministic order
        selected {{ settingsReplacement.pluginId }}.
      </template>
      <template v-else>
        Settings is replaced by {{ settingsReplacement.pluginId }}.
      </template>
      <router-link :to="{ path: '/settings', query: { host: '1' } }">
        Open host Settings
      </router-link>
    </p>
    <PluginContributionHost
      :plugin-id="settingsReplacement.pluginId"
      :document="settingsReplacement.document"
      :page-id="settingsReplacement.page.id"
      :context="{ host_page: 'settings' }"
      embedded
    />
  </main>
  <main v-else class="settings-page">
    <AccountChip fixed />
    <div class="settings-layout">
      <nav class="settings-areas" aria-label="Settings areas">
        <button
          v-for="next in [
            'preferences',
            'account',
            ...(currentUser?.is_admin ? ['administration'] : []),
          ]"
          :key="next"
          type="button"
          :class="{ active: area === next }"
          :aria-current="area === next ? 'page' : undefined"
          @click="openArea(next)"
        >
          {{ areaNames[next as keyof typeof areaNames] }}
        </button>
      </nav>
      <button
        v-if="selectedSection"
        type="button"
        class="section-back"
        @click="backToArea"
      >
        <AppIcon name="chevron" :size="15" />{{ areaNames[area] }}
      </button>
      <PageHeader
        :title="sectionTitle"
        :eyebrow="selectedSection ? areaNames[area] : undefined"
        :description="areaDescriptions[area]"
      >
        <template #actions><SaveStatus /></template>
      </PageHeader>
      <p v-if="area === 'administration'" class="server-scope">
        <AppIcon name="admin" :size="18" /><span
          >Administration · Changes apply to the entire server.</span
        >
      </p>
      <div class="settings-body">
        <SettingsNav
          v-if="selectedSection"
          class="desktop-settings-nav"
          :active-section="activeSection"
          :groups="areaGroups"
          @update:active-section="openSection"
        />
        <div v-if="!selectedSection" class="settings-landing">
          <section
            v-for="group in areaGroups"
            :key="group.label"
            class="settings-landing-group"
          >
            <h2>{{ group.label }}</h2>
            <div class="settings-links">
              <button
                v-for="section in group.sections"
                :key="section.id"
                type="button"
                @click="openSection(section.id)"
              >
                <span>{{ section.label }}</span
                ><AppIcon name="chevron" :size="18" />
              </button>
            </div>
          </section>
        </div>
        <div
          v-else
          ref="card"
          class="settings-card"
          tabindex="-1"
          :aria-label="sectionTitle"
        >
          <ProfileSection v-if="activeSection === 'profile'" />
          <InterfaceSection v-else-if="activeSection === 'interface'" />
          <AppearanceSection v-else-if="activeSection === 'appearance'" />
          <BrandingSection
            v-else-if="activeSection === 'branding' && currentUser?.is_admin"
          />
          <CalendarNotificationsSection
            v-else-if="activeSection === 'notifications'"
            part="notifications"
          />
          <CalendarNotificationsSection
            v-else-if="activeSection === 'calendar'"
            part="calendar"
          />
          <KeyboardShortcutsSection v-else-if="activeSection === 'shortcuts'" />
          <ConnectionsSection
            v-else-if="activeSection === 'connections'"
            @navigate="openSection"
          />
          <ApiKeysSection v-else-if="activeSection === 'api-keys'" />
          <UploadSection v-else-if="activeSection === 'upload'" />
          <LibrarySettings
            v-else-if="activeSection === 'library'"
            :key="'library' + initialTab"
            :initial-tab="initialTab"
          />
          <PluginManagerSection
            v-else-if="activeSection === 'plugins' && currentUser?.is_admin"
          />
          <template v-else-if="activeSection === 'export'">
            <ExportImportSection />
            <AniListImportSection />
          </template>
          <MetadataSettings
            v-else-if="activeSection === 'metadata'"
            :key="'metadata' + initialTab"
            :initial-tab="initialTab"
          />
          <StatsSection v-else-if="activeSection === 'stats'" />
          <AdminSettings
            v-else-if="activeSection === 'admin' && currentUser?.is_admin"
            :key="'admin' + initialTab"
            :initial-tab="initialTab"
          />
          <TasksSection
            v-else-if="activeSection === 'tasks' && currentUser?.is_admin"
          />
          <PluginContributionHost
            v-else-if="activePluginSettings"
            :plugin-id="activePluginSettings.pluginId"
            :document="activePluginSettings.document"
            :page-id="activePluginSettings.pageId"
            embedded
          />
          <PluginContributionHost
            v-else-if="activePluginSettingsNavigation?.pageId"
            :plugin-id="activePluginSettingsNavigation.pluginId"
            :document="activePluginSettingsNavigation.document"
            :page-id="activePluginSettingsNavigation.pageId"
            :context="{ host_page: 'settings' }"
            embedded
          />
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.settings-page {
  position: relative;
  min-height: 100vh;
  box-sizing: border-box;
  padding: 84px var(--ui-edge-right) 48px var(--ui-edge-left);
  background: var(--ui-bg);
  font-family: var(--ui-font-family);
}
.replacement-notice {
  margin: 0 0 16px;
  color: var(--ui-accent-text);
}
.replacement-notice a {
  margin-left: 8px;
  color: inherit;
}
.settings-layout {
  width: 100%;
  max-width: var(--ui-content-width);
  margin: auto;
  color: var(--ui-text);
}
.settings-areas {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-bottom: 18px;
  margin-bottom: 30px;
  border-bottom: 1px solid var(--ui-border-soft);
}
.settings-areas button {
  min-height: var(--ui-control-height);
  padding: 10px 18px;
  border: 0;
  border-radius: 999px;
  color: var(--ui-dim);
  background: transparent;
  cursor: pointer;
  font: inherit;
  font-size: var(--ui-font-small);
  font-weight: 500;
}
.settings-areas button:hover {
  background: var(--ui-surface-2);
}
.settings-areas button.active {
  color: var(--ui-accent-text);
  background: var(--ui-accent-soft);
}
.section-back {
  display: none;
}
.settings-body {
  display: flex;
  gap: 32px;
  align-items: flex-start;
}
.settings-card {
  flex: 1;
  min-width: 0;
  scroll-margin-top: 20px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-card);
  padding: 28px;
  box-sizing: border-box;
}
.settings-card :deep(input:not([type="checkbox"]):not([type="radio"])),
.settings-card :deep(select),
.settings-card :deep(button) {
  min-height: var(--ui-control-height);
}
.settings-landing {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 28px;
  width: 100%;
  max-width: 1040px;
}
.settings-landing-group h2 {
  font-size: var(--ui-font-small);
  font-weight: 600;
  color: var(--ui-dim);
  margin: 0 0 12px 4px;
}
.settings-links {
  background: var(--ui-surface);
  border: 1px solid var(--ui-border-soft);
  border-radius: var(--ui-radius-card);
  padding: 4px 18px;
}
.settings-links button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  min-height: 60px;
  padding: 16px 4px;
  border: 0;
  border-bottom: 1px solid var(--ui-border-soft);
  color: var(--ui-text);
  background: transparent;
  font: inherit;
  font-size: var(--ui-font-body);
  text-align: left;
  cursor: pointer;
}
.settings-links button:last-child {
  border-bottom: 0;
}
.settings-links button:hover {
  color: var(--ui-accent-text);
}
.settings-links button svg {
  color: var(--ui-faint);
  flex-shrink: 0;
}
.server-scope {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  margin: 0 0 24px;
  background: var(--ui-accent-soft);
  color: var(--ui-accent-text);
  border-radius: var(--ui-radius-control);
  font-size: var(--ui-font-small);
}
@media (max-width: 1100px) {
  .settings-body {
    gap: 20px;
  }
  .desktop-settings-nav {
    width: 170px;
  }
  .settings-card {
    padding: 22px;
  }
}
@media (max-width: 760px) {
  .settings-page {
    padding-top: 80px;
  }
  .settings-areas {
    margin-bottom: 24px;
    gap: 4px;
    padding-bottom: 16px;
  }
  .settings-areas button {
    padding: 10px 13px;
  }
  .settings-landing {
    grid-template-columns: minmax(0, 1fr);
    gap: 24px;
  }
  .settings-links {
    padding: 3px 20px;
  }
  .settings-links button {
    min-height: 64px;
  }
  .desktop-settings-nav {
    display: none;
  }
  .settings-card {
    width: 100%;
    padding: 20px;
  }
  .section-back {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    min-height: 44px;
    margin: -12px 0 12px -6px;
    padding: 8px 6px;
    border: 0;
    background: transparent;
    color: var(--ui-accent-text);
    font: inherit;
    font-size: var(--ui-font-small);
    cursor: pointer;
  }
  .section-back svg {
    transform: rotate(180deg);
  }
}
</style>
