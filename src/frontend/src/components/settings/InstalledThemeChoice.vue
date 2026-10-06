<script setup lang="ts">
import { computed } from "vue";
import { currentUser } from "../../state/auth";
import {
  themeCatalogue,
  themesLoaded,
  themesError,
  refreshThemes,
} from "../../state/themes";
import { resolvedUiTheme } from "../../state/uiAppearance";
import { resolveInstalledTheme } from "../../services/themes";

const props = defineProps<{ selection: string; saving: boolean }>();
const emit = defineEmits<{ change: [id: string] }>();
const current = computed(() =>
  resolveInstalledTheme(
    themeCatalogue.value,
    props.selection,
    resolvedUiTheme.value,
  ),
);
const unavailable = computed(
  () =>
    themesLoaded.value &&
    !themesError.value &&
    props.selection !== "native" &&
    (props.selection !== "server" ||
      themeCatalogue.value.default_theme !== "native") &&
    !current.value,
);
const serverName = computed(
  () =>
    themeCatalogue.value.themes.find(
      (theme) => theme.id === themeCatalogue.value.default_theme,
    )?.name ?? "Native interface",
);
</script>

<template>
  <section
    class="installed-theme-choice"
    aria-labelledby="installed-theme-heading"
  >
    <h2 id="installed-theme-heading">Interface theme</h2>
    <p class="section-hint">
      Use an installed theme, or choose native colors with your own palette. The
      preview follows the current light or dark mode.
    </p>
    <div v-if="themesError" class="ui-alert" role="alert">
      {{ themesError }}
      <button type="button" class="ui-btn ui-btn-ghost" @click="refreshThemes">
        Retry
      </button>
    </div>
    <div
      v-else
      class="theme-choice-layout"
      :class="{ 'theme-choice-native': !current }"
    >
      <div>
        <label for="installed-theme">Style</label>
        <select
          id="installed-theme"
          class="ui-field"
          :value="selection"
          :disabled="saving || !themesLoaded"
          @change="emit('change', ($event.target as HTMLSelectElement).value)"
        >
          <option value="server">Server default · {{ serverName }}</option>
          <option value="native">Native interface · choose colors</option>
          <option
            v-for="theme in themeCatalogue.themes"
            :key="theme.id"
            :value="theme.id"
          >
            {{ theme.name }}
          </option>
          <option
            v-if="
              selection !== 'native' &&
              selection !== 'server' &&
              !themeCatalogue.themes.some((theme) => theme.id === selection)
            "
            :value="selection"
          >
            Unavailable theme
          </option>
        </select>
        <p v-if="current" class="section-hint">
          {{ current.description }} {{ current.publisher }} · v{{
            current.version
          }}
        </p>
        <p v-if="current" class="section-hint">
          This theme supplies the interface colors and style. Your native
          palette is kept for when you return to the native interface.
          <button
            type="button"
            class="ui-btn ui-btn-ghost"
            :disabled="saving"
            @click="emit('change', 'native')"
          >
            Choose native colors
          </button>
        </p>
        <p v-if="unavailable" class="section-hint" role="status">
          This theme is unavailable in the current color mode. The native
          interface is shown; your choice is retained.
        </p>
        <RouterLink
          v-if="currentUser?.is_admin"
          to="/settings?area=administration&section=themes"
          >Manage installed themes</RouterLink
        >
      </div>
      <div
        v-if="current"
        class="theme-menu-preview"
        aria-label="Current interface theme preview"
      >
        <strong>{{ current.name }} preview</strong>
        <button type="button" class="ui-btn ui-btn-primary">
          Selected item
        </button>
        <button type="button" class="ui-btn ui-btn-ghost">Another item</button>
        <label
          >Example control
          <select class="ui-field">
            <option>Current theme</option>
            <option>Another choice</option>
          </select></label
        >
      </div>
    </div>
    <slot v-if="!current" />
  </section>
</template>

<style scoped>
.installed-theme-choice {
  margin-top: 28px;
}
h2 {
  margin: 0 0 12px;
  color: var(--ui-text);
  font: var(--ui-weight-heading) var(--ui-font-heading)/1.4
    var(--ui-font-family);
}
.section-hint {
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
  line-height: 1.6;
}
.theme-choice-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 0.8fr);
  gap: 24px;
}
.theme-choice-native {
  grid-template-columns: minmax(0, 1fr);
}
label {
  display: grid;
  gap: 8px;
  font-size: var(--ui-font-small);
}
#installed-theme {
  width: 100%;
  margin-top: 8px;
}
a {
  color: var(--ui-accent-text);
}
.theme-menu-preview {
  display: grid;
  gap: 10px;
  align-content: start;
  padding: 20px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  background: var(--ui-surface-2);
}
@media (max-width: 700px) {
  .theme-choice-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
