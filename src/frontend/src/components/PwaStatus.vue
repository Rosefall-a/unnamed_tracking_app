<script setup lang="ts">
import { computed } from "vue";
import { currentUser } from "../state/auth";
import { pwaState, reloadPwa } from "../services/pwa";

const standalone =
  window.matchMedia("(display-mode: standalone)").matches ||
  (navigator as Navigator & { standalone?: boolean }).standalone === true ||
  new URL(window.location.href).searchParams.get("pwa") === "1";
const visible = computed(
  () =>
    (standalone &&
      (!pwaState.online ||
        (pwaState.available && !pwaState.enabled) ||
        !!pwaState.message)) ||
    (!!currentUser.value && pwaState.enabled && pwaState.updatePending),
);
</script>

<template>
  <aside
    v-if="visible"
    class="pwa-status"
    aria-label="Installed application status"
    aria-live="polite"
  >
    <span v-if="!pwaState.online">Waiting for internet.</span>
    <span v-else-if="pwaState.available && !pwaState.enabled">
      PWA plugin is not enabled. This shortcut opens the ordinary website.
      <RouterLink to="/settings?section=app-installation"
        >Open app installation settings</RouterLink
      >
    </span>
    <span v-else-if="pwaState.message">{{ pwaState.message }}</span>
    <span v-if="pwaState.updatePending">
      App updated. Reload after saving your changes.
      <button type="button" @click="reloadPwa">Reload</button>
    </span>
  </aside>
</template>

<style scoped>
.pwa-status {
  box-sizing: border-box;
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: var(--ui-z-notice);
  width: min(420px, calc(100vw - 48px));
  padding: 16px;
  background: var(--ui-surface);
  color: var(--ui-text);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  box-shadow: var(--ui-elevation);
  font-family: var(--ui-font-family);
  font-size: 0.9rem;
}
.pwa-status:empty {
  display: none;
}
button {
  margin-left: 0.5rem;
  min-height: var(--ui-control-height);
  border: 1px solid var(--ui-border-strong);
  border-radius: var(--ui-radius-control);
  padding: 0.35rem 0.65rem;
  background: var(--ui-surface-2);
  color: inherit;
  font: inherit;
  cursor: pointer;
}
a {
  color: var(--ui-accent);
}
button:focus-visible,
a:focus-visible {
  outline: 2px solid var(--ui-accent);
  outline-offset: 3px;
}
@media (max-width: 760px) {
  .pwa-status {
    bottom: calc(92px + env(safe-area-inset-bottom));
  }
}
</style>
