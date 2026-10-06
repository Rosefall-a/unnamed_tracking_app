<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { currentUser } from "../../state/auth";
import { branding } from "../../state/branding";
import {
  installPwa,
  pwaState,
  refreshPwa,
  reloadPwa,
} from "../../services/pwa";

const display = window.matchMedia("(display-mode: standalone)");
const standalone = ref(
  display.matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true,
);
const ios =
  /iPad|iPhone|iPod/.test(navigator.userAgent) ||
  (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
function updateDisplay() {
  standalone.value =
    display.matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true;
}
onMounted(() => {
  display.addEventListener("change", updateDisplay);
  void refreshPwa();
});
onBeforeUnmount(() => display.removeEventListener("change", updateDisplay));
</script>

<template>
  <section class="installation-section" aria-label="App installation">
    <h2>Install on this device</h2>
    <p>
      Open {{ branding.app_name }} from your home screen or desktop with the
      same library, sign-in and appearance settings.
    </p>
    <div class="installation-card" aria-live="polite">
      <template v-if="!pwaState.available">
        <strong>Installation status unavailable</strong>
        <p>{{ pwaState.message || "Checking the PWA plugin…" }}</p>
        <button type="button" class="secondary" @click="refreshPwa">
          Check again
        </button>
      </template>
      <template v-else-if="!pwaState.enabled">
        <strong>The PWA plugin is disabled</strong>
        <p v-if="currentUser?.is_admin">
          Enable the PWA plugin before installing the app on this device.
        </p>
        <p v-else>
          Ask your administrator to enable the PWA plugin before installing the
          app.
        </p>
        <RouterLink v-if="currentUser?.is_admin" to="/settings?section=plugins"
          >Open plugin settings</RouterLink
        >
      </template>
      <template v-else-if="standalone">
        <strong>You’re using the installed app</strong>
        <p>
          Its colors follow Appearance & interface, including System mode and
          your custom palette.
        </p>
      </template>
      <template v-else>
        <strong>Installation is available with the PWA plugin</strong>
        <p v-if="ios">In Safari, use Share → Add to Home Screen.</p>
        <template v-else>
          <button
            type="button"
            :disabled="!pwaState.installable || !pwaState.online"
            @click="installPwa"
          >
            Install {{ branding.app_name }}
          </button>
          <p v-if="!pwaState.installable">
            If your browser supports installation, use its install menu. The
            browser controls when an install prompt is available.
          </p>
        </template>
        <p v-if="pwaState.message">{{ pwaState.message }}</p>
      </template>
      <p v-if="!pwaState.online">Reconnect to install or check for updates.</p>
      <p v-if="pwaState.updatePending">
        An update is ready. Save your changes, then
        <button type="button" class="secondary" @click="reloadPwa">
          Reload the app</button
        >.
      </p>
    </div>
    <p>
      Installation requires HTTPS or localhost and a supported browser. Offline,
      the app shows a reconnect page in your last device colors. Account data
      and API responses are never cached.
    </p>
  </section>
</template>

<style scoped>
.installation-section {
  display: grid;
  gap: 16px;
  max-width: 760px;
}
h2,
p {
  margin: 0;
}
h2 {
  font-size: var(--ui-font-heading);
  font-weight: var(--ui-weight-heading);
}
p {
  color: var(--ui-dim);
  line-height: 1.6;
}
.installation-card {
  display: grid;
  justify-items: start;
  gap: 16px;
  padding: 20px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface);
}
button {
  min-height: var(--ui-control-height);
  padding: 10px 16px;
  border: 1px solid var(--ui-accent);
  border-radius: var(--ui-radius-control);
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}
button.secondary {
  background: var(--ui-surface-2);
  border-color: var(--ui-border-strong);
  color: var(--ui-text);
}
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
a {
  display: inline-flex;
  align-items: center;
  min-height: var(--ui-control-height);
  color: var(--ui-accent);
}
</style>
