<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import PluginContributionHost from "../components/plugins/PluginContributionHost.vue";
import PageHeader from "../components/PageHeader.vue";
import { currentUser } from "../state/auth";
import {
  fetchPluginUi,
  pluginPathForPage,
  resolvePluginPageId,
  type PluginUiDocument,
} from "../services/pluginUi";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
const document = ref<PluginUiDocument | null>(null);
const loading = ref(true);
const error = ref("");
const activePageId = ref<string | undefined>();
const isArchive = computed(
  () => route.params.pluginId === "official.collectors-archive",
);
let loadGeneration = 0;
const viewerContext = computed(() => {
  const context: Record<string, string | number | boolean> = {};
  for (const key of ["document_id", "game_id", "record_id"] as const) {
    const value = route.query[key];
    if (typeof value === "string") context[key] = value;
  }
  return context;
});

function requestedPluginPath(): string | undefined {
  const value = route.params.pluginPath;
  if (Array.isArray(value)) return value.join("/");
  return typeof value === "string" ? value : undefined;
}

async function load() {
  const generation = ++loadGeneration;
  loading.value = true;
  error.value = "";
  try {
    const loaded = await fetchPluginUi(String(route.params.pluginId));
    if (generation !== loadGeneration) return;
    document.value = loaded;
    activePageId.value = resolvePluginPageId(
      document.value,
      requestedPluginPath(),
    );
    if (!activePageId.value && requestedPluginPath())
      throw new Error("Plugin route not found.");
  } catch (err) {
    if (generation !== loadGeneration) return;
    error.value =
      err instanceof Error ? err.message : "Failed to load plugin UI.";
  } finally {
    if (generation === loadGeneration) loading.value = false;
  }
}

function navigate(pageId: string) {
  activePageId.value = pageId;
  void router.replace({
    name: "plugin-route",
    params: {
      pluginId: String(route.params.pluginId),
      pluginPath: document.value
        ? pluginPathForPage(document.value, pageId)
        : pageId,
    },
  });
}

watch(
  () => route.params.pluginPath,
  () => {
    if (!document.value) return;
    activePageId.value = resolvePluginPageId(
      document.value,
      requestedPluginPath(),
    );
  },
);
watch(
  () => route.params.pluginId,
  () => void load(),
);
onMounted(load);
</script>

<template>
  <main class="plugin-page">
    <p v-if="loading">Loading plugin…</p>
    <section v-else-if="error" class="ui-panel">
      <PageHeader
        :title="isArchive ? 'Collector’s Archive' : 'Plugin page unavailable'"
      />
      <p class="error" role="alert">{{ error }}</p>
      <p v-if="isArchive">
        Cards, Sets and Bounties now belong to the official Collector’s Archive
        plugin. Install and enable it, then import your retained records from
        its settings page.
      </p>
      <p v-else>
        Check that the plugin is enabled, compatible with this host and has its
        required UI permissions.
      </p>
      <RouterLink
        v-if="currentUser?.is_admin"
        to="/settings?area=administration&section=plugins"
        class="ui-btn ui-btn-primary"
        >Open plugin manager</RouterLink
      >
      <p v-else>
        Ask your administrator to check the plugin’s installation and health.
      </p>
    </section>
    <PluginContributionHost
      v-else-if="document && activePageId"
      :plugin-id="document.plugin_id"
      :document="document"
      :page-id="activePageId"
      :context="viewerContext"
      :key="route.fullPath"
      @navigate="navigate"
    />
  </main>
</template>

<style scoped>
.plugin-page {
  min-height: 100vh;
  padding: var(--ui-space-6) var(--ui-edge-right) 60px var(--ui-edge-left);
  background: var(--ui-bg);
  color: var(--ui-text);
}
.error {
  color: var(--ui-error);
}
</style>
