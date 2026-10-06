<script setup lang="ts">
import { computed } from "vue";
import type { PluginInstallPermission } from "../../services/plugins";
const props = defineProps<{ permissions: PluginInstallPermission[] }>();
const counts = computed(() =>
  ["critical", "high", "medium", "low"]
    .map((risk) => ({
      risk,
      count: props.permissions.filter((item) => item.risk === risk).length,
    }))
    .filter((item) => item.count > 0),
);
</script>
<template>
  <div class="risk-summary" aria-label="Requested permission risks">
    <strong>{{ permissions.length }} scopes</strong>
    <span
      v-for="item in counts"
      :key="item.risk"
      class="risk-bubble"
      :class="item.risk"
    >
      {{ item.count }}
      {{
        item.risk === "high"
          ? "High Risk"
          : item.risk === "medium"
            ? "Medium Risk"
            : item.risk === "low"
              ? "Low Risk"
              : "Critical"
      }}
    </span>
  </div>
</template>
<style scoped>
.risk-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin: 12px 0;
}
.risk-bubble {
  border: 1px solid currentColor;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.85rem;
}
.critical {
  color: var(--ui-error);
  background: var(--ui-danger-soft);
}
.high {
  color: var(--ui-warning);
  background: var(--ui-warning-soft);
}
.medium {
  color: var(--ui-warning);
  background: var(--ui-warning-soft);
}
.low {
  color: var(--ui-good);
  background: var(--ui-good-soft);
}
</style>
