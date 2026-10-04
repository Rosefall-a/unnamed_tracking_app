<script setup lang="ts">
import { computed, onErrorCaptured, ref, watch } from "vue";
import type {
  PluginActionContext,
  PluginUiDocument,
  UiAction,
  UiValues,
} from "../../services/pluginUi";
import { dispatchPluginAction } from "../../services/pluginUi";
import { approvePluginAction } from "../../services/pluginUi";
import {
  nativePluginComponents,
  nativePluginFailures,
} from "../../state/pluginNative";
import { activePluginDocuments } from "../../state/pluginExtensions";
import PluginUiHost from "./PluginUiHost.vue";

const props = defineProps<{
  pluginId: string;
  document: PluginUiDocument;
  pageId: string;
  context?: Record<string, string | number | boolean>;
  embedded?: boolean;
  actionContext?: PluginActionContext;
  widgetConfig?: UiValues;
}>();
const emit = defineEmits<{ navigate: [pageId: string]; failed: [] }>();

const failed = ref(false);
const active = computed(() =>
  Boolean(activePluginDocuments.value[props.pluginId]),
);
const component = computed(
  () => nativePluginComponents.value[`${props.pluginId}:${props.pageId}`],
);
const activationFailed = computed(() =>
  Boolean(nativePluginFailures.value[props.pluginId]),
);

watch(
  () => `${props.pluginId}:${props.pageId}:${String(component.value)}`,
  () => (failed.value = false),
);

onErrorCaptured(() => {
  failed.value = true;
  emit("failed");
  return false;
});

async function save(values: UiValues) {
  const response = await fetch(
    `/api/plugins/${encodeURIComponent(props.pluginId)}/settings`,
    {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    },
  );
  if (!response.ok) throw new Error("Plugin settings could not be saved.");
}

async function run(action: UiAction, values: UiValues) {
  await dispatchPluginAction(
    props.pluginId,
    action.id,
    values,
    props.actionContext,
    Boolean(action.confirmation),
  );
}

const nativeHost = computed(() => ({
  runAction: async (actionId: string, values: Record<string, unknown> = {}) => {
    const action = props.document.actions.find((item) => item.id === actionId);
    if (!action) throw new Error("Plugin action not found.");
    if (!approvePluginAction(action, window.confirm))
      return { cancelled: true };
    return dispatchPluginAction(
      props.pluginId,
      actionId,
      values,
      props.actionContext,
      Boolean(action.confirmation),
    );
  },
}));
</script>

<template>
  <p
    v-if="active && (failed || activationFailed)"
    class="plugin-failure"
    role="status"
  >
    This plugin contribution failed and was removed from the page.
  </p>
  <component
    :is="component"
    v-else-if="active && component"
    :key="`${pluginId}:${pageId}:${actionContext?.resource_id ?? ''}`"
    :plugin-id="pluginId"
    :page-id="pageId"
    :context="context ?? {}"
    :host="nativeHost"
    :widget-config="widgetConfig ?? {}"
  />
  <PluginUiHost
    v-else-if="active"
    :document="document"
    :page-id="pageId"
    :context="context"
    :embedded="embedded"
    :widget-config="widgetConfig"
    @save="save"
    @action="run"
    @navigate="emit('navigate', $event)"
  />
</template>

<style scoped>
.plugin-failure {
  padding: 12px;
  border: 1px solid var(--ui-error);
  border-radius: var(--ui-radius-control);
  color: var(--ui-error);
}
</style>
