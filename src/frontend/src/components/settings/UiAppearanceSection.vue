<script setup lang="ts">
import { ref } from "vue";
import {
  preferences,
  preferencesLoaded,
  preferencesError,
  loadSharedPreferences,
} from "../../state/preferences";
import { queuePreferences, type Preferences } from "../../services/preferences";
import { currentUser } from "../../state/auth";

const saving = ref(false);
const error = ref<string | null>(null);
const saved = ref(false);
async function change(changes: Partial<Preferences>) {
  const accountId = currentUser.value?.id;
  const previous = { ...preferences.value };
  preferences.value = { ...previous, ...changes };
  saving.value = true;
  error.value = null;
  saved.value = false;
  try {
    const result = await queuePreferences(changes);
    if (result.latest) preferences.value = result.prefs;
    saved.value = true;
  } catch (reason) {
    if (currentUser.value?.id !== accountId) return;
    preferences.value = previous;
    error.value =
      reason instanceof Error ? reason.message : "Could not save appearance.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <section class="appearance-preferences" aria-labelledby="appearance-heading">
    <h2 id="appearance-heading">Theme & layout</h2>
    <p class="section-hint">
      Your appearance follows your account between devices.
    </p>
    <p v-if="!preferencesLoaded" role="status">Loading appearance…</p>
    <div v-else-if="preferencesError" role="alert" class="ui-alert">
      {{ preferencesError }}
      <button
        type="button"
        class="ui-btn ui-btn-ghost"
        @click="loadSharedPreferences"
      >
        Retry
      </button>
    </div>
    <fieldset v-else :disabled="saving" class="appearance-fields">
      <div class="appearance-row">
        <div>
          <label for="ui-theme">Theme</label>
          <p>Choose light, dark, or follow your device.</p>
        </div>
        <select
          id="ui-theme"
          class="ui-field"
          :value="preferences.ui_theme"
          @change="
            change({
              ui_theme: ($event.target as HTMLSelectElement)
                .value as Preferences['ui_theme'],
            })
          "
        >
          <option value="system">System</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </select>
      </div>
      <div class="appearance-row">
        <div>
          <label for="ui-density">Density</label>
          <p>Adjust spacing without shrinking touch targets.</p>
        </div>
        <select
          id="ui-density"
          class="ui-field"
          :value="preferences.ui_density"
          @change="
            change({
              ui_density: ($event.target as HTMLSelectElement)
                .value as Preferences['ui_density'],
            })
          "
        >
          <option value="comfortable">Comfortable</option>
          <option value="compact">Compact</option>
        </select>
      </div>
      <div class="appearance-row">
        <div>
          <label for="ui-motion">Reduce motion</label>
          <p>The device’s reduced-motion preference is always respected.</p>
        </div>
        <input
          id="ui-motion"
          type="checkbox"
          :checked="preferences.ui_reduce_motion"
          @change="
            change({
              ui_reduce_motion: ($event.target as HTMLInputElement).checked,
            })
          "
        />
      </div>
      <div class="appearance-row">
        <div>
          <label for="ui-contrast">Higher contrast</label>
          <p>Stronger text, boundaries, and keyboard focus.</p>
        </div>
        <input
          id="ui-contrast"
          type="checkbox"
          :checked="preferences.ui_high_contrast"
          @change="
            change({
              ui_high_contrast: ($event.target as HTMLInputElement).checked,
            })
          "
        />
      </div>
    </fieldset>
    <p v-if="error" class="ui-error" role="alert">{{ error }}</p>
    <p class="appearance-status" role="status" aria-live="polite">
      {{ saving ? "Saving…" : saved ? "Appearance saved" : "" }}
    </p>
  </section>
</template>

<style scoped>
.appearance-preferences {
  margin-bottom: var(--ui-space-8);
}
h2 {
  margin: 0 0 12px;
  font: var(--ui-weight-heading) var(--ui-font-heading)/1.4
    var(--ui-font-family);
  color: var(--ui-text);
}
.section-hint {
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
  margin-bottom: 16px;
}
.appearance-fields {
  padding: 0 20px;
  margin: 0;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface);
}
.appearance-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding: var(--ui-row-padding) 0;
  border-bottom: 1px solid var(--ui-border-soft);
}
.appearance-row:last-child {
  border: 0;
}
label {
  color: var(--ui-text);
  font-size: var(--ui-font-body);
  font-weight: 500;
}
.appearance-row p {
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
  margin: 5px 0 0;
  line-height: 1.5;
}
select {
  flex-shrink: 0;
  max-width: 155px;
}
input[type="checkbox"] {
  width: 22px;
  height: 22px;
  accent-color: var(--ui-accent);
  flex-shrink: 0;
}
.appearance-status {
  min-height: 20px;
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
  margin-top: 10px;
}
@media (max-width: 480px) {
  .appearance-row {
    flex-wrap: wrap;
    gap: 10px;
  }
  select {
    max-width: 100%;
  }
}
</style>
