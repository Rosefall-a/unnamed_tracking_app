<script setup lang="ts">
import { computed } from "vue";
import type { PluginCompatibilityCheck } from "../../services/plugins";
const props = defineProps<{
  versions: {
    version: string;
    api_contract_version?: string;
    host_api_contract_version?: string;
    sdk_version_range?: string;
    host_sdk_version?: string;
    application_version_range?: string;
    host_application_version?: string;
    compatibility_checks?: PluginCompatibilityCheck[];
  };
}>();
const rows = computed(() =>
  [
    {
      key: "api_contract",
      title: "UI/API contract",
      text: `Plugin ${props.versions.api_contract_version ?? "1.0.0"} · Host ${props.versions.host_api_contract_version ?? "Not reported"}`,
    },
    {
      key: "sdk",
      title: "Plugin SDK",
      text: `Required ${props.versions.sdk_version_range ?? "Not reported"} · Host ${props.versions.host_sdk_version ?? "Not reported"}`,
    },
    {
      key: "application",
      title: "Application compatibility",
      text: `Required ${props.versions.application_version_range ?? "Not reported"} · Host ${props.versions.host_application_version ?? "Not reported"}`,
    },
  ].map((row) => ({
    ...row,
    check: props.versions.compatibility_checks?.find(
      (check) => check.key === row.key,
    ),
  })),
);
</script>

<template>
  <section class="version-info" aria-label="Plugin version requirements">
    <h3>Versions & compatibility</h3>
    <dl>
      <div>
        <dt>Plugin release</dt>
        <dd>{{ versions.version }}</dd>
      </div>
      <div
        v-for="row in rows"
        :key="row.key"
        :class="row.check?.status"
        :aria-label="`${row.title}${row.check ? ': ' + row.check.status : ''}`"
      >
        <dt>
          {{ row.title }}
          <strong v-if="row.check" class="status">{{
            row.check.status === "incompatible"
              ? "Incompatible"
              : row.check.status === "limited"
                ? "Limited support"
                : "Supported"
          }}</strong>
        </dt>
        <dd>{{ row.text }}</dd>
        <p v-if="row.check && row.check.status !== 'supported'" class="reason">
          {{ row.check.reason }}
        </p>
      </div>
    </dl>
    <p>
      Plugin release numbers are independent of the UI/API contract. A newer
      release still needs a compatible declared contract and version ranges.
    </p>
  </section>
</template>

<style scoped>
.version-info {
  padding: var(--ui-space-4);
  margin: var(--ui-space-4) 0;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface-2);
}
h3 {
  margin: 0 0 var(--ui-space-3);
  font-size: var(--ui-font-body);
}
dl {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr));
  gap: var(--ui-space-3);
  margin: 0;
}
dl > div {
  min-width: 0;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  padding: var(--ui-space-3);
}
.status {
  display: inline-block;
  margin-left: var(--ui-space-2);
  color: var(--ui-text);
}
dl > .incompatible {
  border: 2px solid var(--ui-error);
  background: var(--ui-danger-soft);
}
.incompatible .status,
.incompatible .reason {
  color: var(--ui-error);
}
dl > .limited {
  border-color: var(--ui-warning);
  background: var(--ui-warning-soft);
}
.limited .status,
.limited .reason {
  color: var(--ui-warning);
}
dt,
p {
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
}
dd {
  color: var(--ui-text);
  margin: 4px 0 0;
  overflow-wrap: anywhere;
  line-height: 1.5;
}
p {
  margin: var(--ui-space-3) 0 0;
  line-height: 1.5;
}
</style>
