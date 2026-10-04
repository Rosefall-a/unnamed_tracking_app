<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watchEffect } from "vue";
import UiModal from "./UiModal.vue";
import { preferences } from "../state/preferences";
import { currentUser } from "../state/auth";
import { queuePreferences } from "../services/preferences";
import { applyPalette } from "../services/uiPalette";
import { resolveUiTheme, type UiAppearance } from "../state/uiAppearance";

const accountId = currentUser.value?.id;
const choices = ref<UiAppearance>({
  ui_theme: preferences.value.ui_theme,
  ui_palette: preferences.value.ui_palette,
  ui_custom_palette: preferences.value.ui_custom_palette,
  ui_density: preferences.value.ui_density,
  ui_style: preferences.value.ui_style,
  ui_reduce_motion: preferences.value.ui_reduce_motion,
  ui_high_contrast: preferences.value.ui_high_contrast,
});
const system = window.matchMedia("(prefers-color-scheme: dark)");
const systemDark = ref(system.matches);
const updateSystem = () => {
  systemDark.value = system.matches;
};
system.addEventListener("change", updateSystem);
onBeforeUnmount(() => system.removeEventListener("change", updateSystem));
const mode = computed(() =>
  resolveUiTheme(choices.value.ui_theme, systemDark.value),
);
const preview = ref<HTMLElement | null>(null);
watchEffect(() => {
  if (preview.value)
    applyPalette(
      preview.value,
      choices.value.ui_palette,
      mode.value,
      choices.value.ui_custom_palette,
      choices.value.ui_high_contrast,
    );
});
const saving = ref(false);
const error = ref("");
async function finish() {
  if (saving.value || currentUser.value?.id !== accountId) return;
  saving.value = true;
  error.value = "";
  try {
    const result = await queuePreferences({
      ...choices.value,
      ui_welcome_completed: true,
    });
    if (currentUser.value?.id === accountId && result.latest)
      preferences.value = result.prefs;
  } catch (reason) {
    if (currentUser.value?.id === accountId)
      error.value =
        reason instanceof Error
          ? reason.message
          : "Could not save your appearance.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <UiModal
    title="Make yourself at home"
    description="Choose your appearance. You can change these choices and create or import a palette later in Preferences → Appearance."
    size="wide"
    :dismissible="false"
  >
    <div class="welcome-layout">
      <fieldset :disabled="saving" class="welcome-choices">
        <legend>Your interface</legend>
        <label for="welcome-theme">Theme</label>
        <select id="welcome-theme" v-model="choices.ui_theme" class="ui-field">
          <option value="system">System</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </select>
        <label for="welcome-palette">Color palette</label>
        <select
          id="welcome-palette"
          v-model="choices.ui_palette"
          class="ui-field"
        >
          <option value="orange">Orange</option>
          <option value="green">Green</option>
          <option v-if="choices.ui_palette === 'custom'" value="custom">
            Current custom palette
          </option>
        </select>
        <label for="welcome-density">Spacing</label>
        <select
          id="welcome-density"
          v-model="choices.ui_density"
          class="ui-field"
        >
          <option value="comfortable">Comfortable</option>
          <option value="compact">Compact</option>
        </select>
        <label class="welcome-check"
          ><input type="checkbox" v-model="choices.ui_reduce_motion" /> Reduce
          motion</label
        >
        <label class="welcome-check"
          ><input type="checkbox" v-model="choices.ui_high_contrast" /> Higher
          contrast</label
        >
        <p>
          Your choices follow your account. This browser also remembers the
          appearance for sign-in and offline screens.
        </p>
      </fieldset>
      <section
        ref="preview"
        class="welcome-preview"
        :data-theme="mode"
        :data-density="choices.ui_density"
        aria-label="Appearance preview"
      >
        <p class="preview-label">
          {{ mode === "dark" ? "Dark" : "Light" }} preview
        </p>
        <h3>Your library, your way</h3>
        <div class="preview-menu" aria-label="Example menu">
          <span class="preview-selected">Library</span><span>Collections</span
          ><span>Statistics</span>
        </div>
        <div class="preview-card">
          <strong>A little progress goes a long way</strong>
          <p>Keep your games, media and collections together.</p>
          <span class="preview-status">Completed</span>
        </div>
        <button type="button" class="ui-btn ui-btn-primary" disabled>
          Example action
        </button>
      </section>
    </div>
    <p v-if="error" class="ui-error" role="alert">{{ error }}</p>
    <template #footer
      ><button
        type="button"
        class="ui-btn ui-btn-primary"
        :disabled="saving"
        @click="finish"
      >
        {{ saving ? "Saving…" : "Save & continue" }}
      </button></template
    >
  </UiModal>
</template>

<style scoped>
.welcome-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 32px;
}
.welcome-choices {
  border: 0;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 12px;
  min-width: 0;
}
.welcome-choices legend {
  font-weight: 600;
  margin-bottom: 16px;
}
.welcome-choices p,
.preview-label {
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
  line-height: 1.6;
}
.welcome-check {
  display: flex;
  gap: 12px;
  align-items: center;
  min-height: 44px;
}
.welcome-check input {
  width: 22px;
  height: 22px;
  accent-color: var(--ui-accent);
}
.welcome-preview {
  padding: 24px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  background: var(--ui-bg);
  color: var(--ui-text);
  min-width: 0;
}
.welcome-preview h3 {
  font-size: var(--ui-font-heading);
  margin: 16px 0;
}
.preview-menu {
  display: grid;
  padding: 8px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
}
.preview-menu span {
  padding: 12px;
  border-radius: var(--ui-radius-control);
}
.welcome-preview[data-density="compact"] .preview-menu span {
  padding: 8px 12px;
}
.preview-selected {
  background: var(--ui-accent-soft);
  color: var(--ui-accent);
  font-weight: 600;
}
.preview-card {
  margin: 20px 0;
  padding: 20px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface);
}
.preview-card p {
  color: var(--ui-dim);
  line-height: 1.6;
}
.preview-status {
  color: var(--ui-success);
}
.welcome-preview .ui-btn:disabled {
  opacity: 1;
}
@media (max-width: 700px) {
  .welcome-layout {
    grid-template-columns: minmax(0, 1fr);
    gap: 24px;
  }
  .welcome-preview {
    padding: 20px;
  }
}
</style>
