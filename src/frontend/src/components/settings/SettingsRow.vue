<script setup lang="ts">
// One setting: its name and a short hint on the left, the control on the
// right. stack puts a wide control (a long picker) on its own line underneath.
defineProps<{ label: string; hint?: string; stack?: boolean }>();
</script>

<template>
  <div class="st-row" :class="{ stack }">
    <div class="st-lbl">
      <strong>{{ label }}</strong>
      <span v-if="hint || $slots.hint"
        ><slot name="hint">{{ hint }}</slot></span
      >
    </div>
    <slot />
  </div>
</template>
