<script setup lang="ts">
import { computed } from "vue";
import {
  RouterLink,
  useRoute,
  useRouter,
  type RouteLocationRaw,
} from "vue-router";
import type { PluginNavigationContribution } from "../../state/pluginExtensions";
import {
  approvePluginAction,
  dispatchPluginAction,
} from "../../services/pluginUi";
import {
  navigationShortcutForPath,
  navigationTooltip,
} from "../../utils/shortcuts";
import NavFolderList from "../NavFolderList.vue";
import AppIcon from "../AppIcon.vue";

const props = defineProps<{
  items: PluginNavigationContribution[];
  collapsed: boolean;
}>();
const emit = defineEmits<{ navigate: []; error: [message: string] }>();
const router = useRouter();
const route = useRoute();
const entries = computed(() =>
  props.items.map((item) => ({
    ...item,
    id: `${item.pluginId}:${item.contributionId}`,
  })),
);
function target(item: PluginNavigationContribution): RouteLocationRaw {
  if (item.settingsSectionId)
    return {
      path: "/settings",
      query: { section: item.settingsSectionId, area: item.area },
    };
  return {
    name: "plugin-route",
    params: {
      pluginId: item.pluginId,
      pluginPath: item.routePath || item.pageId,
    },
  };
}
function active(item: PluginNavigationContribution): boolean {
  if (item.action) return false;
  const path = router.resolve(target(item)).path;
  return route.path === path || route.path.startsWith(`${path}/`);
}
const activeIds = computed(() =>
  entries.value.filter(active).map((item) => item.id),
);
async function activate(item: PluginNavigationContribution) {
  if (!item.action) {
    emit("navigate");
    return;
  }
  if (!approvePluginAction(item.action, window.confirm)) return;
  try {
    await dispatchPluginAction(
      item.pluginId,
      item.action.id,
      {},
      undefined,
      Boolean(item.action.confirmation),
    );
    emit("navigate");
  } catch (error) {
    emit(
      "error",
      error instanceof Error
        ? error.message
        : "Could not run the plugin action.",
    );
  }
}
</script>

<template>
  <NavFolderList
    :entries="entries"
    :active-ids="activeIds"
    :collapsed="collapsed"
  >
    <template #default="{ entry }">
      <component
        :is="entry.action ? 'button' : RouterLink"
        :to="entry.action ? undefined : target(entry)"
        :type="entry.action ? 'button' : undefined"
        class="plugin-sidebar-item"
        :class="{ active: active(entry), collapsed }"
        :aria-label="entry.label"
        :aria-current="active(entry) ? 'page' : undefined"
        :title="
          entry.action
            ? entry.label
            : navigationTooltip(entry.label, router.resolve(target(entry)).path)
        "
        :aria-keyshortcuts="
          entry.action
            ? undefined
            : navigationShortcutForPath(router.resolve(target(entry)).path)
        "
        @click="activate(entry)"
      >
        <span
          v-if="entry.icon"
          class="plugin-sidebar-icon"
          aria-hidden="true"
          >{{ entry.icon }}</span
        >
        <AppIcon v-else name="plugin" />
        <span v-if="!collapsed">{{ entry.label }}</span>
      </component>
    </template>
  </NavFolderList>
</template>

<style scoped>
.plugin-sidebar-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  width: 100%;
  padding: 10px 12px;
  border: 0;
  border-radius: var(--ui-radius-row);
  background: transparent;
  color: var(--ui-dim);
  font: inherit;
  font-size: 14px;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
  touch-action: manipulation;
}
.plugin-sidebar-item:hover {
  background: var(--ui-surface-2);
  color: var(--ui-text);
}
.plugin-sidebar-item.active {
  background: var(--ui-accent-soft);
  color: var(--ui-accent-text);
}
.plugin-sidebar-item > span {
  overflow-wrap: anywhere;
}
.plugin-sidebar-icon {
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}
.plugin-sidebar-item.collapsed {
  justify-content: center;
  padding-inline: 0;
}
</style>
