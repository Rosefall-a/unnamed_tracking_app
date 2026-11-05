<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import SettingsTabs from "./SettingsTabs.vue";
import AdminSection from "./AdminSection.vue";
import OidcSettingsSection from "./OidcSettingsSection.vue";
import ServerIntegrationsSection from "./ServerIntegrationsSection.vue";
import LimitsSection from "./LimitsSection.vue";
import DevToolsSection from "./DevToolsSection.vue";
import BackupsSection from "./BackupsSection.vue";
import RepairSection from "./RepairSection.vue";

const props = defineProps<{ initialTab?: string }>();

// Admin-only server settings in one place. Tasks and Logs keep their own
// entries in the sidebar.
const TABS = [
  { id: "users", label: "Users" },
  { id: "backups", label: "Backups" },
  { id: "repair", label: "Repair" },
  { id: "sso", label: "Single sign-on" },
  { id: "integrations", label: "Integrations" },
  { id: "limits", label: "Limits" },
  { id: "dev-tools", label: "Dev Tools" },
];
const tab = ref(
  TABS.some((t) => t.id === props.initialTab) ? props.initialTab! : "users",
);

// In the URL so a refresh stays on this tab. section is named here because
// Settings may still be switching to it when this first runs.
const route = useRoute();
const router = useRouter();
watch(
  tab,
  (value) => {
    if (route.query.tab === value) return;
    void router.replace({
      query: { ...route.query, section: "admin", tab: value },
    });
  },
  { immediate: true },
);
</script>

<template>
  <div>
    <SettingsTabs v-model="tab" :tabs="TABS" />
    <AdminSection v-if="tab === 'users'" />
    <BackupsSection v-else-if="tab === 'backups'" />
    <RepairSection v-else-if="tab === 'repair'" />
    <OidcSettingsSection v-else-if="tab === 'sso'" />
    <ServerIntegrationsSection v-else-if="tab === 'integrations'" />
    <LimitsSection v-else-if="tab === 'limits'" />
    <DevToolsSection v-else />
  </div>
</template>
