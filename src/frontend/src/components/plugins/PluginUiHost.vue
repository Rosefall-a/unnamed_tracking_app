<script setup lang="ts">
import {
  readPluginAppearance,
  observePluginAppearance,
} from "../../services/pluginAppearance";
import PluginField from "./PluginField.vue";
import { navigationShortcutForKey } from "../../utils/shortcuts";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  approvePluginAction,
  buildInitialValues,
  dispatchPluginAction,
  downloadPluginDocument,
  PluginActionError,
  validateField,
  type PluginUiDocument,
  type UiAction,
  type UiField,
  type UiValues,
} from "../../services/pluginUi";

const props = defineProps<{
  document: PluginUiDocument;
  tableData?: Record<string, Record<string, string | number | boolean>[]>;
  pageId?: string;
  embedded?: boolean;
  context?: Record<string, string | number | boolean>;
  widgetConfig?: UiValues;
}>();
const emit = defineEmits<{
  action: [action: UiAction, values: UiValues];
  save: [values: UiValues];
  navigate: [pageId: string];
}>();
const activePage = ref(props.pageId ?? props.document.pages[0]?.id ?? "");
const values = ref<UiValues>(buildInitialValues(props.document));
const submitted = ref(false);
const iframe = ref<HTMLIFrameElement | null>(null);
const iframeHeight = ref(520);
const frontend = computed(() =>
  props.embedded ? undefined : props.document.frontend,
);
const frontendUrl = computed(() =>
  frontend.value
    ? `/api/plugins/${encodeURIComponent(props.document.plugin_id)}/frontend/${frontend.value.entry.split("/").map(encodeURIComponent).join("/")}`
    : "",
);
const pages = computed(() => props.document.pages);
const page = computed(
  () =>
    pages.value.find((item) => item.id === activePage.value) ?? pages.value[0],
);
const settings = computed(() =>
  props.document.settings.filter((item) =>
    page.value?.settings.includes(item.id),
  ),
);
const actions = computed(() =>
  props.document.actions.filter((item) =>
    page.value?.actions.includes(item.id),
  ),
);
const tables = computed(() =>
  props.document.tables.filter((item) => page.value?.tables.includes(item.id)),
);
const dialogs = computed(() =>
  props.document.dialogs.filter((item) =>
    page.value?.dialogs.includes(item.id),
  ),
);
const errors = computed(() => {
  if (!submitted.value) return [];
  return settings.value.flatMap((section) =>
    section.fields
      .map((field) => ({
        field: field.id,
        message: validateField(field, values.value[field.id]),
      }))
      .filter(
        (item): item is { field: string; message: string } =>
          item.message !== null,
      ),
  );
});
function errorFor(field: UiField): string | undefined {
  return errors.value.find((item) => item.field === field.id)?.message;
}
function submit() {
  submitted.value = true;
  if (!errors.value.length) {
    const saved = Object.fromEntries(
      settings.value.flatMap((section) =>
        section.fields
          .filter((field) => !field.secret)
          .map((field) => [field.id, values.value[field.id]]),
      ),
    );
    emit("save", saved);
  }
}
function runAction(action: UiAction) {
  if (!approvePluginAction(action, window.confirm)) return;
  emit("action", action, {
    ...values.value,
    ...(props.widgetConfig
      ? { _widget_configuration: JSON.stringify(props.widgetConfig) }
      : {}),
    _plugin_context: JSON.stringify({
      page_id: page.value?.id ?? "",
      page_title: page.value?.title ?? "",
      path: window.location.pathname,
      ...props.context,
    }),
  });
}
function goTo(pageId: string) {
  activePage.value = pageId;
  emit("navigate", pageId);
}
async function handleFrontendMessage(event: MessageEvent) {
  if (
    event.source !== iframe.value?.contentWindow ||
    !event.data ||
    event.data.type !== "plugin-api-request"
  )
    return;
  const { requestId, method, payload } = event.data as {
    requestId?: unknown;
    method?: unknown;
    payload?: unknown;
  };
  if (
    typeof requestId !== "string" ||
    typeof method !== "string" ||
    !payload ||
    typeof payload !== "object"
  )
    return;
  try {
    const data = payload as Record<string, unknown>;
    let result: Record<string, unknown> = {};
    if (method === "plugin.save-secret") {
      const key = String(data.key || "");
      const value = String(data.value || "");
      const response = await fetch(
        `/api/plugins/${encodeURIComponent(props.document.plugin_id)}/secrets/${encodeURIComponent(key)}`,
        {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value }),
        },
      );
      if (!response.ok) throw new Error("Plugin secret could not be saved.");
      result = { saved: true };
    } else if (method === "plugin.save-settings") {
      const response = await fetch(
        `/api/plugins/${encodeURIComponent(props.document.plugin_id)}/settings`,
        {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        },
      );
      if (!response.ok) throw new Error("Plugin settings could not be saved.");
      result = { saved: true };
    } else if (method === "plugin.run-action") {
      const action = props.document.actions.find(
        (item) => item.id === String(data.actionId),
      );
      if (!action) throw new Error("Plugin action not found.");
      if (!approvePluginAction(action, window.confirm)) {
        result = { cancelled: true };
        iframe.value?.contentWindow?.postMessage(
          { type: "plugin-api-response", requestId, result },
          "*",
        );
        return;
      }
      result = await dispatchPluginAction(
        props.document.plugin_id,
        action.id,
        data.values && typeof data.values === "object"
          ? (data.values as Record<string, unknown>)
          : {},
        undefined,
        Boolean(action.confirmation),
      );
    } else if (method === "plugin.download-document") {
      await downloadPluginDocument(
        props.document.plugin_id,
        String(data.document_id ?? ""),
      );
      result = { download_started: true };
    } else if (method === "plugin.resize") {
      if (typeof data.height !== "number" || !Number.isFinite(data.height))
        throw new Error("Plugin frame height must be a finite number.");
      iframeHeight.value = Math.min(
        2400,
        Math.max(320, Math.ceil(data.height)),
      );
      result = { height: iframeHeight.value };
    } else if (method === "plugin.shortcut") {
      const navigation = navigationShortcutForKey(data.key);
      const global = data.key === "help" || data.key === "search";
      if (!navigation && !global)
        throw new Error("Unknown host navigation shortcut.");
      // The shared keyboard handler retains its modal and palette guards.
      // The frame cannot request arbitrary paths or privileged operations.
      window.dispatchEvent(
        new KeyboardEvent("keydown", {
          key: navigation?.key ?? (data.key === "help" ? "?" : "k"),
          code: navigation
            ? `Key${navigation.key.toUpperCase()}`
            : data.key === "help"
              ? "Slash"
              : "KeyK",
          altKey: Boolean(navigation),
          ctrlKey: data.key === "search",
          bubbles: true,
        }),
      );
      result = { supported: true };
    } else if (method === "plugin.theme") {
      result = { ...readPluginAppearance() };
    } else if (method === "plugin.context") {
      result = {
        plugin_id: props.document.plugin_id,
        path: window.location.pathname,
        appearance: readPluginAppearance(),
        ...props.context,
      };
    } else {
      throw new Error("Unknown plugin frontend API method.");
    }
    iframe.value?.contentWindow?.postMessage(
      { type: "plugin-api-response", requestId, result },
      "*",
    );
  } catch (error) {
    iframe.value?.contentWindow?.postMessage(
      {
        type: "plugin-api-response",
        requestId,
        error:
          error instanceof Error ? error.message : "Plugin API request failed.",
        status_code:
          error instanceof PluginActionError ? error.status : undefined,
      },
      "*",
    );
  }
}
watch(
  () => props.pageId,
  (pageId) => {
    if (pageId && props.document.pages.some((item) => item.id === pageId))
      activePage.value = pageId;
  },
);
function sendAppearance() {
  iframe.value?.contentWindow?.postMessage(
    {
      type: "plugin-appearance-changed",
      appearance: readPluginAppearance(),
    },
    "*",
  );
}
let stopAppearance = () => {};
onMounted(() => {
  window.addEventListener("message", handleFrontendMessage);
  stopAppearance = observePluginAppearance(sendAppearance);
});
onBeforeUnmount(() => {
  window.removeEventListener("message", handleFrontendMessage);
  stopAppearance();
});
</script>

<template>
  <section class="plugin-ui-host" :aria-label="document.title">
    <header>
      <h2>{{ embedded ? page?.title : document.title }}</h2>
      <nav
        v-if="
          !embedded && !frontend && (document.menus.length || pages.length > 1)
        "
        aria-label="Plugin navigation"
      >
        <button
          v-for="menu in document.menus"
          :key="menu.id"
          type="button"
          @click="
            menu.page_id
              ? goTo(menu.page_id)
              : menu.action_id &&
                runAction(
                  document.actions.find((item) => item.id === menu.action_id)!,
                )
          "
        >
          {{ menu.label }}
        </button>
        <button
          v-for="item in pages"
          :key="'page-' + item.id"
          type="button"
          :class="{ active: item.id === page?.id }"
          @click="goTo(item.id)"
        >
          {{ item.title }}
        </button>
      </nav>
      <p v-if="!frontend && page?.description" class="muted">
        {{ page.description }}
      </p>
    </header>
    <div v-if="frontend" class="frontend-shell">
      <iframe
        ref="iframe"
        :style="{ height: `${iframeHeight}px` }"
        :src="frontendUrl"
        :title="document.title + ' frontend'"
        sandbox="allow-scripts"
        loading="lazy"
        @load="sendAppearance"
      ></iframe>
    </div>
    <p v-else-if="!page" class="empty">This plugin has no native pages.</p>
    <template v-else>
      <form @submit.prevent="submit">
        <fieldset v-for="section in settings" :key="section.id">
          <legend>{{ section.title }}</legend>
          <p v-if="section.description" class="muted">
            {{ section.description }}
          </p>
          <PluginField
            v-for="field in section.fields"
            :key="field.id"
            v-model="values[field.id]"
            :field="field"
            :error="errorFor(field)"
          />
        </fieldset>
        <div v-for="table in tables" :key="table.id" class="table-block">
          <h3>{{ table.title }}</h3>
          <table v-if="props.tableData?.[table.id]?.length">
            <thead>
              <tr>
                <th v-for="column in table.columns" :key="column.id">
                  {{ column.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, index) in props.tableData[table.id]"
                :key="index"
              >
                <td v-for="column in table.columns" :key="column.id">
                  {{ row[column.id] }}
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else class="muted">{{ table.empty_message }}</p>
        </div>
        <div v-for="dialog in dialogs" :key="dialog.id" class="dialog">
          <h3>{{ dialog.title }}</h3>
          <p>{{ dialog.body }}</p>
          <div class="actions">
            <button
              v-for="id in dialog.actions"
              :key="id"
              type="button"
              @click="
                document.actions.find((item) => item.id === id) &&
                runAction(document.actions.find((item) => item.id === id)!)
              "
            >
              {{ document.actions.find((item) => item.id === id)?.label || id }}
            </button>
          </div>
        </div>
        <div class="actions">
          <button type="submit">Save</button
          ><button
            v-for="action in actions"
            :key="action.id"
            type="button"
            @click="runAction(action)"
          >
            {{ action.label }}
          </button>
        </div>
      </form>
    </template>
  </section>
</template>
<style scoped>
.plugin-ui-host {
  display: grid;
  gap: 24px;
}
header {
  display: grid;
  gap: 8px;
}
nav,
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
button {
  min-height: var(--ui-control-height);
  padding: 10px 14px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  background: var(--ui-surface-2);
  color: var(--ui-text);
  font: inherit;
  cursor: pointer;
}
nav button.active {
  color: var(--ui-accent-text);
  background: var(--ui-accent-soft);
  border-color: var(--ui-accent-line);
  font-weight: 700;
}
fieldset,
.dialog,
.table-block {
  display: grid;
  min-width: 0;
  overflow-x: auto;
  gap: 12px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-row);
  padding: 16px;
}
legend {
  padding: 0 6px;
  font-weight: 700;
}
label {
  display: grid;
  gap: 5px;
}
label > span {
  font-weight: 600;
}
small,
.muted {
  color: var(--ui-dim);
}
.error {
  color: var(--ui-error);
  font-style: normal;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  text-align: left;
  padding: 8px;
  border-bottom: 1px solid var(--ui-border);
}
.empty {
  color: var(--ui-dim);
}
.frontend-shell {
  min-height: 520px;
}
.frontend-shell iframe {
  display: block;
  width: 100%;
  min-height: 520px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-row);
  background: var(--ui-surface-2);
}
</style>
