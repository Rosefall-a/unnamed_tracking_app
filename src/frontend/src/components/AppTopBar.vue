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
  z-index: 80;
  display: flex;
  align-items: center;
  gap: 16px;
  box-sizing: border-box;
  min-height: 68px;
  padding: 10px 244px 10px 64px;
  background: rgba(13, 13, 13, 0.94);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid #202020;
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
/* On a phone the switcher and the page's actions can't share one line: both
   wrapped into tall stacks that overlapped each other. The switcher keeps the
   first line (between the menu button and the account chip) and scrolls
   sideways if it still doesn't fit, with tabs that have an icon showing only
   the icon unless active. The actions get their own full-width line below. */
@media (max-width: 720px) {
  .media-topbar {
    flex-wrap: wrap;
    row-gap: 10px;
    padding: 10px 16px;
  }
  .topbar-left {
    flex: 1 1 100%;
    box-sizing: border-box;
    min-height: 48px;
    /* margins, not padding: a scrolling box clips at its padding edge, so
       padding would let the tabs slide under the menu button and the chip */
    margin: 0 228px 0 46px;
    flex-wrap: nowrap;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .topbar-left::-webkit-scrollbar {
    display: none;
  }
  .topbar-left :deep(.seg) {
    flex-wrap: nowrap;
    flex-shrink: 0;
  }
  .topbar-left :deep(.seg-tab:not(.active):has(svg)) {
    padding: 0 10px;
  }
  .topbar-left :deep(.seg-tab:not(.active) svg + .seg-label) {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
  .media-topbar-actions {
    flex: 1 1 100%;
    margin-left: 0;
    justify-content: flex-start;
  }
}
@media (max-width: 520px) {
  .topbar-left {
    margin-right: 96px;
  }
}
/* the narrowest phones: the active tab goes icon-only too (the page heading
   just below still names the section) */
@media (max-width: 420px) {
  .topbar-left :deep(.seg-tab:has(svg)) {
    padding: 0 10px;
  }
  .topbar-left :deep(.seg-tab svg + .seg-label) {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
}
</style>
