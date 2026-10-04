<script setup lang="ts">
// The one sticky top bar every page in the Media area and the Calendar and
// Statistics pages share: fixed minimum height, padding, border and the
// account chip live here once, so nothing shifts when you move between
// pages. Callers fill the left side (default slot) and, optionally, the
// right-hand `actions` slot. The chip is pinned to the bar's right edge and
// the bar reserves room for it, so it stays put even when the left side
// wraps onto more lines on a narrow window.
import AccountChip from "./AccountChip.vue";
</script>

<template>
  <div class="media-topbar">
    <div class="topbar-left"><slot /></div>
    <div v-if="$slots.actions" class="media-topbar-actions">
      <slot name="actions" />
    </div>
    <AccountChip />
  </div>
</template>

<style scoped>
.media-topbar {
  position: sticky;
  top: 0;
  z-index: var(--ui-z-topbar);
  display: flex;
  align-items: center;
  gap: 16px;
  box-sizing: border-box;
  min-height: 68px;
  padding: 12px var(--ui-edge-right) 12px var(--ui-edge-left);
  background: color-mix(in srgb, var(--ui-bg) 94%, transparent);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--ui-border-soft);
}
.media-topbar :deep(.account-chip) {
  position: static;
  margin-left: auto;
  flex-shrink: 0;
}
.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  min-width: 0;
}
.media-topbar-actions {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
  min-width: 0;
  gap: 10px;
}
@media (max-width: 720px) {
  .media-topbar {
    padding-left: var(--ui-edge-left);
  }
}
@media (max-width: 520px) {
  .media-topbar {
    padding-right: var(--ui-edge-right);
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
  }
  .media-topbar :deep(.account-chip) {
    grid-column: 2;
    grid-row: 1;
  }
  .topbar-left {
    grid-column: 1;
    grid-row: 1;
  }
  .topbar-left :deep(.seg-tab) {
    padding-inline: 7px;
    font-size: 0.75rem;
  }
  .media-topbar-actions {
    grid-column: 1 / -1;
    justify-content: flex-start;
    margin-left: 0;
    gap: 6px;
  }
  .media-topbar-actions :deep(.seg-tab) {
    padding-inline: 9px;
  }
}
</style>
