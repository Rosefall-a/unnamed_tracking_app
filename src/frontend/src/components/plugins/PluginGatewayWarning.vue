<script setup lang="ts">
import type { RuntimeCapabilities } from "../../services/plugins";

defineProps<{ runtime: RuntimeCapabilities }>();
</script>

<template>
  <aside
    v-if="runtime.available !== false && runtime.gateway_configured === false"
    class="gateway-warning"
    role="alert"
  >
    <strong>Plugin pages cannot reach the app</strong>
    <p>{{ runtime.gateway_error }}</p>
    <p>
      Installing again will not repair this shared connection. After correcting
      the service configuration, refresh Plugin Manager to check gateway health.
    </p>
    <a
      href="https://github.com/Rosefall-a/unnamed_tracking_app/blob/feat/ui-ux-redevelopment/wiki/docs/development/plugin-runtime.md#gateway-configuration"
      target="_blank"
      rel="noopener noreferrer"
      >Gateway configuration help</a
    >
  </aside>
</template>

<style scoped>
.gateway-warning {
  margin-block: 16px;
  padding: 18px;
  border: 1px solid var(--ui-danger);
  border-left-width: 4px;
  border-radius: var(--ui-radius-card);
  background: color-mix(in srgb, var(--ui-danger) 10%, var(--ui-surface));
  color: var(--ui-text);
}
.gateway-warning p {
  margin-block: 8px;
  overflow-wrap: anywhere;
}
.gateway-warning a {
  color: var(--ui-accent);
}
</style>
