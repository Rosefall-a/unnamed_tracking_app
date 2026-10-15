<script setup lang="ts">
// A line across the page, with a label if you want one, to start a new section.
import { computed } from "vue";
import type { WidgetProps } from "../../../home/registry";

const props = defineProps<WidgetProps>();

const label = computed(() => String(props.settings.label ?? "").trim());
const look = computed(() => String(props.settings.look ?? "line"));
const big = computed(() => props.settings.size === "large");
const center = computed(() => props.settings.align === "center");
</script>

<template>
  <div class="divider" :class="[look, { big, center }]">
    <span v-if="label" class="label">{{ label }}</span>
    <span class="rule"></span>
  </div>
</template>

<style scoped>
.divider {
  display: flex;
  align-items: center;
  gap: 14px;
  height: 100%;
  color: var(--ui-text);
}
.divider.center {
  justify-content: center;
}
.divider.center::before {
  content: "";
  flex: 1;
  height: 0;
  border-top: 1px solid var(--ui-border-strong);
}
.label {
  flex: none;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--ui-dim);
}
.big .label {
  font-size: 1.25rem;
  letter-spacing: 0;
  text-transform: none;
  color: var(--ui-heading);
  font-weight: 800;
}
.rule {
  flex: 1;
  height: 0;
  border-top: 1px solid var(--ui-border-strong);
}
.dotted .rule,
.dotted.center::before {
  border-top-style: dotted;
  border-top-width: 2px;
}
.glow .rule,
.glow.center::before {
  height: 2px;
  border: 0;
  background: linear-gradient(
    90deg,
    var(--ui-accent),
    color-mix(in srgb, var(--ui-accent) 0%, transparent)
  );
}
.glow.center::before {
  background: linear-gradient(
    270deg,
    var(--ui-accent),
    color-mix(in srgb, var(--ui-accent) 0%, transparent)
  );
}
</style>
