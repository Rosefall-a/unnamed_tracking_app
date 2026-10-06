<script setup lang="ts">
import { ref, watch } from "vue";
import { branding } from "../state/branding";
import AppIcon from "./AppIcon.vue";

defineProps<{ compact?: boolean }>();
const failed = ref(false);
watch(
  () => branding.value.logo_url,
  () => {
    failed.value = false;
  },
);
</script>

<template>
  <span class="app-brand">
    <span class="app-brand-symbol" aria-hidden="true">
      <img
        v-if="branding.logo_url && !failed"
        :src="branding.logo_url"
        alt=""
        @error="failed = true"
      />
      <AppIcon v-else name="collections" :size="24" />
    </span>
    <span v-if="!compact" class="app-brand-name">{{ branding.app_name }}</span>
  </span>
</template>

<style scoped>
.app-brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.app-brand-symbol {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 13px;
  background: var(--ui-accent-soft);
  color: var(--ui-accent);
}
.app-brand-symbol img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: inherit;
}
.app-brand-name {
  font-size: 18px;
  font-weight: 650;
  overflow-wrap: anywhere;
}
</style>
