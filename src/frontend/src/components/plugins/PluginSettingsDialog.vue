<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import UiModal from "../UiModal.vue";
import PermissionRiskSummary from "./PermissionRiskSummary.vue";
import PluginPermissionAccess from "./PluginPermissionAccess.vue";
import PluginVersionInfo from "./PluginVersionInfo.vue";
import PluginReadme from "./PluginReadme.vue";
import type {
  PluginPermissionGrant,
  PluginPermissionRequest,
} from "../../services/pluginPermissions";
import type { PluginDiagnostics, PluginSummary } from "../../services/plugins";
import {
  pluginIssues,
  recentPluginEvents,
} from "../../services/pluginDiagnostics";
import type {
  PluginUiDocument,
  UiAction,
  UiValues,
} from "../../services/pluginUi";

const props = defineProps<{
  plugin: PluginSummary;
  document: PluginUiDocument | null;
  grants: PluginPermissionGrant[];
  requests: PluginPermissionRequest[];
  diagnostics: PluginDiagnostics | null;
  loading: boolean;
  busy: boolean;
  error?: string;
}>();
const emit = defineEmits<{
  close: [];
  save: [values: UiValues];
  action: [action: UiAction, values: UiValues];
  enable: [];
  disable: [];
  retry: [];
  revoke: [grantId: string];
  approve: [requestId: string];
  deny: [requestId: string];
  refresh: [];
  update: [];
  operation: [operation: string, purge?: boolean];
  autoUpdate: [mode: string];
  grant: [key: string];
  deleteHistory: [id: string];
}>();

type Tab = "overview" | "settings" | "permissions" | "diagnostics";
const tab = ref<Tab>("overview");
const closeButton = ref<HTMLButtonElement | null>(null);
const permissions = computed(() => props.plugin.permission_details ?? []);
const issues = computed(() => pluginIssues(props.plugin));

const diagnosticEvents = computed(() =>
  recentPluginEvents(props.diagnostics?.events ?? []),
);

watch(
  () => props.plugin.plugin_id,
  async () => {
    tab.value = "overview";
    await nextTick();
    closeButton.value?.focus();
  },
  { immediate: true },
);
</script>

<template>
  <UiModal
    size="wide"
    :title="plugin.name"
    :dismissible="!busy"
    @close="emit('close')"
  >
    <section class="plugin-dialog">
      <header class="dialog-header">
        <div>
          <p class="eyebrow">Plugin settings</p>
          <img
            v-if="plugin.icon"
            :src="plugin.icon"
            alt=""
            width="48"
            height="48"
          />

          <p>{{ plugin.plugin_id }} · v{{ plugin.version }}</p>
          <p>{{ plugin.description }}</p>
          <p>
            Publisher:
            {{
              plugin.trust?.publisher_identity ??
              plugin.publisher ??
              "Unverified"
            }}
          </p>
        </div>
        <button
          ref="closeButton"
          type="button"
          aria-label="Close plugin settings"
          :disabled="busy"
          @click="emit('close')"
        >
          Close
        </button>
      </header>

      <div v-if="!loading" class="actions" aria-label="Plugin controls">
        <button
          v-if="
            plugin.available_update?.update_available || plugin.staged_update
          "
          :disabled="busy"
          @click="emit('update')"
        >
          Review update
          {{
            plugin.available_update?.available_version ??
            plugin.staged_update?.available_version
          }}
        </button>
        <button
          v-if="plugin.enabled"
          :disabled="
            busy || (!plugin.compatible && plugin.status !== 'running')
          "
          @click="
            emit('operation', plugin.status === 'running' ? 'stop' : 'start')
          "
        >
          {{ plugin.status === "running" ? "Stop" : "Start" }}
        </button>
        <button :disabled="busy" @click="emit('operation', 'reinstall')">
          Reinstall this release
        </button>
        <button
          class="danger"
          :disabled="busy"
          @click="emit('operation', 'reinstall', true)"
        >
          Reinstall and purge data
        </button>
        <button
          class="danger"
          :disabled="busy"
          @click="emit('operation', 'uninstall')"
        >
          Uninstall and purge data
        </button>
        <button
          v-if="plugin.enabled"
          type="button"
          :disabled="busy"
          @click="emit('disable')"
        >
          Disable
        </button>
        <button
          v-else
          type="button"
          :disabled="busy || !plugin.compatible"
          class="primary"
          @click="emit('enable')"
        >
          Enable
        </button>
        <button
          v-if="plugin.status === 'failed' || plugin.status === 'quarantined'"
          type="button"
          :disabled="busy"
          @click="emit('retry')"
        >
          Retry
        </button>
      </div>

      <p v-if="error" class="operation-error" role="alert">{{ error }}</p>

      <nav aria-label="Plugin settings sections">
        <button
          v-for="item in [
            'overview',
            'settings',
            'permissions',
            'diagnostics',
          ] as Tab[]"
          :key="item"
          type="button"
          :class="{ active: tab === item }"
          :aria-pressed="tab === item"
          @click="tab = item"
        >
          {{ item[0].toUpperCase() + item.slice(1) }}
        </button>
      </nav>

      <p v-if="loading" class="state">Loading plugin details…</p>
      <template v-else>
        <section v-if="tab === 'overview'" class="panel">
          <dl class="overview-grid">
            <div>
              <dt>Status</dt>
              <dd>{{ plugin.status }}</dd>
            </div>
            <div>
              <dt>Health</dt>
              <dd>{{ plugin.health }}</dd>
            </div>
            <div>
              <dt>Enabled</dt>
              <dd>{{ plugin.enabled ? "Yes" : "No" }}</dd>
            </div>
            <div>
              <dt>Compatibility</dt>
              <dd>
                {{
                  plugin.compatible ? "Compatible" : plugin.compatibility_reason
                }}
              </dd>
            </div>
          </dl>
          <PluginVersionInfo :versions="plugin" />
          <aside
            v-if="plugin.compatibility_warning"
            class="legacy-warning"
            role="status"
          >
            <strong>Built for the old UI · limited support</strong>
            <p>{{ plugin.compatibility_warning }}</p>
          </aside>
          <section v-if="plugin.readme" class="documentation">
            <h3>Plugin documentation</h3>
            <PluginReadme :text="plugin.readme" />
          </section>
          <p v-else-if="plugin.documentation_error" role="status">
            {{ plugin.documentation_error }}
          </p>
          <aside
            v-if="issues.length"
            class="attention"
            aria-label="Plugin issues"
          >
            <h3>Needs attention</h3>
            <p v-for="[source, reason] in issues" :key="source">
              <strong>{{ source }}:</strong> {{ reason }}
            </p>
            <p v-if="!plugin.compatible">
              The whole plugin stays stopped until a verified compatible update
              is installed. Review or upload an update in Plugin Manager.
            </p>
          </aside>
        </section>

        <section v-else-if="tab === 'settings'" class="panel">
          <h3>Plugin Manager settings</h3>
          <p v-if="plugin.version_pin" class="version-pin" role="status">
            Pinned to v{{ plugin.version_pin }}. Installing an older release or
            rolling back disables automatic updates. Choose Enabled or Follow
            global setting below to release the pin.
          </p>
          <label
            >Automatic updates
            <select
              :value="plugin.automatic_updates ?? 'follow'"
              :disabled="busy || plugin.source?.type !== 'catalogue'"
              @change="
                emit('autoUpdate', ($event.target as HTMLSelectElement).value)
              "
            >
              <option value="follow">Follow global setting</option>
              <option value="enabled">Enabled</option>
              <option value="disabled">Disabled</option>
            </select>
          </label>
          <p v-if="plugin.source?.type !== 'catalogue'">
            Automatic tracking requires a catalogue installation.
          </p>
          <RouterLink :to="`/plugins/${encodeURIComponent(plugin.plugin_id)}`"
            >Open plugin application pages and configuration</RouterLink
          >
          <h3>Retained package versions</h3>
          <p>
            Version history is separate from plugin data. Rollback preserves
            data and does not restore revoked grants.
          </p>
          <article
            v-for="version in plugin.history ?? []"
            :key="version.id"
            class="grant"
          >
            <strong>v{{ version.version }}</strong>
            <button
              :disabled="busy"
              @click="emit('operation', `rollback/${version.id}`)"
            >
              Roll back
            </button>
            <button
              class="danger"
              :disabled="busy"
              @click="emit('deleteHistory', version.id)"
            >
              Delete retained package
            </button>
          </article>
        </section>

        <section v-else-if="tab === 'permissions'" class="panel">
          <PermissionRiskSummary :permissions="permissions" />
          <PluginPermissionAccess
            :permissions="permissions"
            :grants="grants"
            :requests="requests"
            :busy="busy"
            @revoke="emit('revoke', $event)"
            @approve="emit('approve', $event)"
            @deny="emit('deny', $event)"
            @grant="emit('grant', $event)"
          />
        </section>

        <section v-else class="panel diagnostics">
          <PluginVersionInfo :versions="plugin" />
          <p v-for="[source, reason] in issues" :key="source" class="state">
            <strong>{{ source }}:</strong> {{ reason }}
          </p>
          <dl class="diagnostic-summary">
            <div>
              <dt>Runtime availability</dt>
              <dd>
                {{
                  plugin.runtime_available === undefined
                    ? "Unknown"
                    : plugin.runtime_available
                      ? "Available"
                      : "Unavailable"
                }}
              </dd>
            </div>
            <div>
              <dt>Isolation</dt>
              <dd>{{ plugin.runtime?.mechanism ?? "Unknown" }}</dd>
            </div>
            <div>
              <dt>Bubblewrap</dt>
              <dd>
                {{
                  plugin.runtime?.bubblewrap_available == null
                    ? "Unknown"
                    : plugin.runtime.bubblewrap_available
                      ? "Usable"
                      : "Unavailable"
                }}
              </dd>
            </div>
            <div>
              <dt>Sandbox</dt>
              <dd>
                {{
                  plugin.runtime_available === false
                    ? "Unavailable"
                    : plugin.runtime?.sandbox_available
                      ? "Active"
                      : plugin.runtime?.reduced_isolation_allowed
                        ? "Reduced isolation"
                        : "Unavailable"
                }}
              </dd>
            </div>
            <div>
              <dt>Reduced isolation allowed</dt>
              <dd>
                {{
                  plugin.runtime?.reduced_isolation_allowed == null
                    ? "Unknown"
                    : plugin.runtime.reduced_isolation_allowed
                      ? plugin.runtime.reduced_isolation_env_override
                        ? "Yes · NONBUBBLE_ENV enabled"
                        : "Yes · administrator acknowledged"
                      : "Awaiting administrator acknowledgement"
                }}
              </dd>
            </div>
            <div class="last-error">
              <dt>Last error</dt>
              <dd>
                {{
                  issues.find(([source]) => source !== "Compatibility")?.[1] ??
                  "None"
                }}
              </dd>
            </div>
          </dl>
          <div class="diagnostic-heading">
            <h3>Runtime diagnostics</h3>
            <button type="button" :disabled="busy" @click="emit('refresh')">
              Refresh
            </button>
          </div>
          <dl v-if="diagnostics" class="diagnostic-summary">
            <div>
              <dt>Status</dt>
              <dd>{{ diagnostics.status }}</dd>
            </div>
            <div>
              <dt>Last exit code</dt>
              <dd>{{ diagnostics.last_exit_code ?? "—" }}</dd>
            </div>
          </dl>
          <ol
            v-if="diagnosticEvents.length"
            class="event-list"
            aria-label="Plugin diagnostic events, newest first"
          >
            <li
              v-for="event in diagnosticEvents"
              :key="event.sequence"
              :data-sequence="event.sequence"
              :class="`level-${event.level}`"
            >
              <div class="event-heading">
                <time :datetime="event.timestamp">{{
                  new Date(event.timestamp).toLocaleString()
                }}</time>
                <strong>{{ event.level }}</strong>
                <code>{{ event.event }}</code>
              </div>
              <p>{{ event.message }}</p>
              <small v-if="event.correlation_id">
                Correlation: {{ event.correlation_id }}
              </small>
            </li>
          </ol>
          <p v-else class="state">No runtime diagnostics are available.</p>
        </section>
      </template>
    </section>
  </UiModal>
</template>

<style scoped>
.documentation {
  padding-block: var(--ui-space-4);
}
.legacy-warning {
  padding: var(--ui-space-4);
  border: 1px solid var(--ui-warning);
  border-radius: var(--ui-radius-card);
  background: var(--ui-warning-soft);
  color: var(--ui-warning);
}
.plugin-dialog {
  color: var(--ui-text);
  overflow-wrap: anywhere;
}
.dialog-header > div {
  min-width: 0;
}
.dialog-header > button {
  flex: 0 0 auto;
  white-space: nowrap;
  overflow-wrap: normal;
}
.operation-error {
  padding: var(--ui-space-4);
  border: 1px solid var(--ui-error);
  border-radius: var(--ui-radius-card);
  background: var(--ui-danger-soft);
  color: var(--ui-error);
  line-height: 1.5;
}
.attention {
  padding: var(--ui-space-4);
  margin: var(--ui-space-4) 0;
  background: var(--ui-warning-soft);
  border: 1px solid var(--ui-border-strong);
  border-radius: var(--ui-radius-card);
}
.attention p {
  margin: 10px 0 0;
  line-height: 1.5;
}
.dialog-header,
.diagnostic-heading,
.actions,
.grant,
.request-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}
.pending {
  border-color: var(--ui-warning);
}
.pending p {
  margin: 6px 0 0;
  color: var(--ui-dim);
}
.dialog-header h2,
.dialog-header p,
h3 {
  margin: 0;
  color: var(--ui-text);
}
.eyebrow {
  color: var(--ui-accent-text) !important;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.dialog-header p,
.state,
small,
dt,
.grant > span {
  color: var(--ui-dim);
}
.dialog-header > button,
nav button,
.actions button,
.grant button,
.diagnostic-heading button {
  min-height: var(--ui-control-height);
  padding: 8px 12px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  background: var(--ui-surface-2);
  color: var(--ui-text);
  cursor: pointer;
}
nav {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin: 20px 0;
  border-bottom: 1px solid var(--ui-border);
}
nav button {
  border: 0;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  background: transparent;
}
nav button.active {
  color: var(--ui-accent-text);
  border-bottom-color: var(--ui-accent-text);
}
.panel {
  min-height: 220px;
}
.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.overview-grid div {
  padding: 14px;
  background: var(--ui-surface-2);
  border-radius: 9px;
}
.overview-grid dd {
  margin: 5px 0 0;
}
.actions {
  flex-wrap: wrap;
  justify-content: flex-start;
  margin-block: var(--ui-space-4);
  padding-block: var(--ui-space-3);
  border-block: 1px solid var(--ui-border);
}
.actions button {
  white-space: nowrap;
  max-width: 100%;
}
.actions .danger {
  border-color: var(--ui-error);
  color: var(--ui-error);
}
.actions .primary {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  border-color: var(--ui-accent-line);
  font-weight: 700;
}
.grant {
  padding: 13px 0;
  border-bottom: 1px solid var(--ui-border);
}
.grant > div {
  display: grid;
  gap: 4px;
}
.grant .danger {
  border-color: var(--ui-error);
  color: var(--ui-error);
}
.diagnostic-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  gap: var(--ui-space-4);
}
.diagnostic-summary > div {
  min-width: 0;
}
.diagnostic-summary .last-error {
  grid-column: 1 / -1;
}
.diagnostic-summary .last-error dd {
  max-height: 12rem;
  overflow: auto;
  overflow-wrap: anywhere;
}
.diagnostic-summary dd {
  margin: 2px 0 0;
  line-height: 1.5;
}
.event-list {
  display: grid;
  gap: 8px;
  max-height: 340px;
  overflow: auto;
  padding: 0;
  list-style: none;
}
.event-list li {
  padding: 12px;
  border-left: 3px solid var(--ui-border-strong);
  border-radius: 6px;
  background: var(--ui-surface-2);
}
.event-list li.level-warning {
  border-left-color: var(--ui-accent-text);
}
.event-list li.level-error {
  border-left-color: var(--ui-error);
}
.event-heading {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.event-heading time,
.event-heading code {
  color: var(--ui-dim);
}
.event-heading strong {
  text-transform: uppercase;
}
.event-list p {
  margin: 8px 0 0;
}
button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
@media (max-width: 620px) {
  .grant {
    flex-wrap: wrap;
  }
  .diagnostic-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
