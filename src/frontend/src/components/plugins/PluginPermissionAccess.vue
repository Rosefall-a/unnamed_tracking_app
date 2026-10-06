<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../AppIcon.vue";
import type { PluginInstallPermission } from "../../services/plugins";
import type {
  PluginPermissionGrant,
  PluginPermissionRequest,
} from "../../services/pluginPermissions";
import {
  permissionAccessRows,
  permissionIcon,
} from "../../services/pluginPermissionAccess";

const props = defineProps<{
  permissions: PluginInstallPermission[];
  grants: PluginPermissionGrant[];
  requests: PluginPermissionRequest[];
  busy: boolean;
}>();
const emit = defineEmits<{
  revoke: [id: string];
  approve: [id: string];
  deny: [id: string];
  grant: [key: string];
}>();
const rows = computed(() =>
  permissionAccessRows(props.permissions, props.grants, props.requests),
);
const groups = computed(() =>
  (
    [
      ["active", "Active access"],
      ["pending", "Pending requests"],
      ["denied", "Denied access"],
    ] as const
  )
    .map(([state, label]) => ({
      state,
      label,
      rows: rows.value.filter((row) => row.state === state),
    }))
    .filter((group) => group.rows.length),
);
</script>

<template>
  <p class="permission-help">
    Review active access or expand denied permissions to restore a scope.
    Permissions are enforced by the gateway and can be revoked immediately.
  </p>
  <p v-if="!rows.length">This plugin requests no host permissions.</p>
  <details
    v-for="group in groups"
    :key="group.state"
    class="access-group"
    :open="group.state !== 'denied'"
  >
    <summary>
      {{ group.label }} <span>{{ group.rows.length }}</span>
    </summary>
    <article v-for="row in group.rows" :key="row.key" class="access-row">
      <span class="permission-icon" :class="row.permission.risk">
        <AppIcon :name="permissionIcon(row.permission.capability)" :size="22" />
      </span>
      <div class="permission-details">
        <small class="category">{{ row.permission.category }}</small>
        <strong>{{ row.permission.title }}</strong>
        <small
          >{{ row.permission.capability }} · v{{
            row.permission.capability_version
          }}</small
        >
        <span class="risk" :class="row.permission.risk"
          >{{ row.permission.risk }} risk</span
        >
        <small>
          {{ row.userId ? `User ${row.userId}` : "All authenticated users" }}
          <template v-if="row.deviceId"> · Device {{ row.deviceId }}</template>
        </small>
        <p v-if="row.request">{{ row.request.rationale }}</p>
        <small v-if="row.coveredBy">Included by {{ row.coveredBy }}</small>
      </div>
      <div class="access-actions">
        <button
          v-if="row.state === 'active' && row.grant"
          class="danger"
          :disabled="busy"
          @click="emit('revoke', row.grant.id)"
        >
          Revoke
        </button>
        <template v-else-if="row.state === 'pending' && row.request">
          <button :disabled="busy" @click="emit('deny', row.request.id)">
            Deny
          </button>
          <button
            class="primary"
            :disabled="busy"
            @click="emit('approve', row.request.id)"
          >
            Allow
          </button>
        </template>
        <button
          v-else-if="row.state === 'denied' && !row.userId && !row.deviceId"
          :disabled="busy"
          @click="emit('grant', row.permission.key)"
        >
          Review and grant
        </button>
        <small v-else-if="row.state === 'denied'"
          >Scoped access withdrawn</small
        >
      </div>
    </article>
  </details>
</template>

<style scoped>
.permission-help {
  color: var(--ui-muted);
  line-height: 1.6;
}
.access-group {
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  margin-block: var(--ui-space-4);
  overflow: hidden;
}
summary {
  cursor: pointer;
  min-height: 48px;
  padding: 14px 18px;
  font-weight: 700;
  background: var(--ui-surface-2);
}
summary span {
  margin-left: 8px;
  color: var(--ui-muted);
}
.access-row {
  display: flex;
  align-items: start;
  gap: 14px;
  padding: 18px;
  border-top: 1px solid var(--ui-border);
}
.permission-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  border: 1px solid currentColor;
  border-radius: var(--ui-radius-control);
}
.permission-details {
  display: grid;
  gap: 5px;
  min-width: 0;
  flex: 1;
  overflow-wrap: anywhere;
}
.permission-details small {
  color: var(--ui-muted);
}
.category {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.risk {
  text-transform: capitalize;
  font-size: 0.8rem;
}
.critical {
  color: var(--ui-error);
}
.high,
.medium {
  color: var(--ui-warning);
}
.low {
  color: var(--ui-good);
}
.permission-icon.critical {
  background: var(--ui-danger-soft);
}
.permission-icon.high,
.permission-icon.medium {
  background: var(--ui-warning-soft);
}
.permission-icon.low {
  background: var(--ui-good-soft);
}
.access-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: end;
}
button {
  min-height: 44px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  padding: 10px 14px;
  color: var(--ui-text);
  background: var(--ui-surface);
  cursor: pointer;
  font: inherit;
}
button.primary {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  border-color: var(--ui-accent);
}
button.danger {
  color: var(--ui-error);
}
button:disabled {
  cursor: wait;
  opacity: 0.6;
}
@media (max-width: 600px) {
  .access-row {
    flex-wrap: wrap;
    padding: 14px;
  }
  .access-actions {
    width: 100%;
    justify-content: start;
    padding-left: 56px;
  }
}
</style>
