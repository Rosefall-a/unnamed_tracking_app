<script setup lang="ts">
defineProps<{
  versions: {
    version: string;
    api_contract_version?: string;
    host_api_contract_version?: string;
    sdk_version_range?: string;
    host_sdk_version?: string;
    application_version_range?: string;
    host_application_version?: string;
  };
}>();
</script>

<template>
  <section class="version-info" aria-label="Plugin version requirements">
    <h3>Versions & compatibility</h3>
    <dl>
      <div>
        <dt>Plugin release</dt>
        <dd>{{ versions.version }}</dd>
      </div>
      <div>
        <dt>UI/API contract</dt>
        <dd>
          Plugin {{ versions.api_contract_version ?? "1.0.0" }} · Host
          {{ versions.host_api_contract_version ?? "Not reported" }}
        </dd>
      </div>
      <div>
        <dt>Plugin SDK</dt>
        <dd>
          Required {{ versions.sdk_version_range ?? "Not reported" }} · Host
          {{ versions.host_sdk_version ?? "Not reported" }}
        </dd>
      </div>
      <div>
        <dt>Application compatibility</dt>
        <dd>
          Required {{ versions.application_version_range ?? "Not reported" }} ·
          Host {{ versions.host_application_version ?? "Not reported" }}
        </dd>
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
