<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { Preferences } from "../../services/preferences";
import {
  ORANGE_PALETTE,
  PALETTE_FIELDS,
  paletteTokens,
  paletteContrastIssues,
  type PaletteId,
  type PaletteMode,
  type PaletteColors,
  type CustomPalette,
} from "../../services/uiPalette";
const props = defineProps<{
  palette: PaletteId;
  custom: CustomPalette;
  saving: boolean;
}>();
const emit = defineEmits<{ change: [value: Partial<Preferences>] }>();
const selected = ref(props.palette);
const mode = ref<PaletteMode>("light");
function copy(colors: CustomPalette): Record<PaletteMode, PaletteColors> {
  return {
    light: { ...ORANGE_PALETTE.light, ...colors.light },
    dark: { ...ORANGE_PALETTE.dark, ...colors.dark },
  };
}
const draft = ref(copy(props.custom));
watch(
  () => [props.palette, props.custom] as const,
  () => {
    selected.value = props.palette;
    draft.value = copy(props.custom);
  },
  { deep: true },
);
const previewStyle = computed(() => ({
  ...paletteTokens(selected.value, mode.value, draft.value),
  colorScheme: mode.value,
}));
const issues = computed(() =>
  selected.value === "custom"
    ? (["light", "dark"] as const).flatMap((theme) =>
        paletteContrastIssues(draft.value[theme]).map(
          (issue) => `${theme}: ${issue}`,
        ),
      )
    : [],
);
function apply() {
  emit("change", {
    ui_palette: selected.value,
    ...(selected.value === "custom"
      ? { ui_custom_palette: copy(draft.value) }
      : {}),
  });
}
</script>

<template>
  <section class="palette-section" aria-labelledby="palette-heading">
    <h2 id="palette-heading">Color palette</h2>
    <p class="section-hint">
      Preview colors before applying them. Each palette has a light and dark
      version; System follows your device.
    </p>
    <fieldset :disabled="saving" class="palette-controls">
      <label for="ui-palette">Palette</label>
      <select id="ui-palette" v-model="selected" class="ui-field">
        <option value="orange">Archive orange</option>
        <option value="green">Garden green</option>
        <option value="custom">Custom colors</option>
      </select>
      <div class="preview-modes" role="group" aria-label="Palette preview mode">
        <button
          v-for="theme in ['light', 'dark'] as const"
          :key="theme"
          type="button"
          class="ui-btn ui-btn-ghost"
          :aria-pressed="mode === theme"
          @click="mode = theme"
        >
          {{ theme === "light" ? "Light preview" : "Dark preview" }}
        </button>
      </div>
      <div class="palette-layout">
        <div v-if="selected === 'custom'" class="color-fields">
          <label
            v-for="[role, label] in PALETTE_FIELDS"
            :key="role"
            class="color-field"
          >
            <span>{{ label }} ({{ mode }})</span>
            <input
              v-model="draft[mode][role]"
              type="color"
              :aria-label="`${label} (${mode})`"
            />
          </label>
          <button
            type="button"
            class="ui-btn ui-btn-ghost"
            @click="draft = copy({})"
          >
            Reset custom colors
          </button>
        </div>
        <div
          class="palette-preview"
          :style="previewStyle"
          aria-label="Palette preview"
        >
          <nav aria-label="Preview navigation" class="preview-menu">
            <button type="button" class="preview-selected">Library</button>
            <button type="button">Collections</button>
            <details>
              <summary>Account menu</summary>
              <div class="preview-dropdown">
                <button type="button">Appearance</button
                ><button type="button">Notifications</button>
              </div>
            </details>
          </nav>
          <div class="preview-card">
            <h3>Your library</h3>
            <p>Menus, cards and top bars share this palette.</p>
            <div class="preview-row">
              <strong>A favorite adventure</strong
              ><span class="preview-success">Completed</span>
            </div>
            <div class="preview-tags">
              <span class="preview-warning">Permission review</span
              ><span class="preview-error">Upload failed</span
              ><span class="preview-info">Update available</span
              ><span class="preview-plan">Plan to play</span>
            </div>
          </div>
          <div class="preview-dialog">
            <h3>Edit collection</h3>
            <label
              >Collection name<input
                value="Weekend favorites"
                aria-label="Preview collection name"
            /></label>
            <div class="preview-actions">
              <button type="button">Cancel</button
              ><button type="button" class="preview-selected">
                Save changes
              </button>
            </div>
          </div>
        </div>
      </div>
      <p v-if="issues.length" class="ui-error" role="status">
        Adjust {{ issues.length }} color pairs to reach readable text contrast
        (4.5:1): {{ issues.slice(0, 4).join("; ")
        }}{{ issues.length > 4 ? "; …" : "" }}.
      </p>
      <p v-else class="section-hint">
        The preview shows both normal menus and a dialog. Custom text and status
        colors are checked against each background.
      </p>
      <button
        type="button"
        class="ui-btn ui-btn-primary"
        :disabled="issues.length > 0"
        @click="apply"
      >
        Apply palette
      </button>
    </fieldset>
  </section>
</template>

<style scoped>
.palette-section {
  margin-block: var(--ui-space-8);
}
h2 {
  font: var(--ui-weight-heading) var(--ui-font-heading)/1.4
    var(--ui-font-family);
}
.section-hint {
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
  line-height: 1.5;
}
.palette-controls {
  border: 0;
  padding: 0;
  margin: 0;
  min-width: 0;
}
.palette-controls > label {
  display: block;
  margin-bottom: 6px;
}
.preview-modes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-block: 16px;
}
.preview-modes [aria-pressed="true"] {
  border-color: var(--ui-accent);
  background: var(--ui-accent-soft);
  color: var(--ui-accent-text);
}
.palette-layout {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));
  gap: 20px;
}
.color-fields {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.color-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: var(--ui-font-small);
}
.color-field input {
  width: 56px;
  height: var(--ui-control-height);
  border: 1px solid var(--ui-border);
  padding: 3px;
  border-radius: var(--ui-radius-control);
  background: var(--ui-surface);
}
.palette-preview {
  background: var(--ui-bg);
  color: var(--ui-text);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  padding: 16px;
  min-width: 0;
}
.palette-preview h3 {
  margin: 0 0 8px;
  font-size: var(--ui-font-heading);
}
.palette-preview p {
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
}
.preview-menu,
.preview-actions,
.preview-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.preview-menu {
  margin-bottom: 16px;
}
.palette-preview button,
.palette-preview summary {
  box-sizing: border-box;
  min-height: var(--ui-control-height);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-control);
  background: var(--ui-surface);
  color: var(--ui-text);
  font: inherit;
  font-size: var(--ui-font-small);
  padding: 8px 12px;
  cursor: pointer;
}
.palette-preview .preview-selected {
  background: var(--ui-accent);
  color: var(--ui-on-accent);
  border-color: var(--ui-accent);
}
.preview-card,
.preview-dialog {
  padding: 16px;
  background: var(--ui-surface);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  margin-bottom: 12px;
}
.preview-dialog {
  margin-bottom: 0;
}
.preview-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 12px;
  background: var(--ui-surface-2);
  border-radius: var(--ui-radius-row);
  margin-bottom: 12px;
  font-size: var(--ui-font-small);
}
.preview-tags span {
  padding: 5px 8px;
  border-radius: 999px;
  font-size: var(--ui-font-small);
}
.preview-success {
  color: var(--ui-good);
}
.preview-warning {
  color: var(--ui-warning);
  background: var(--ui-warning-soft);
}
.preview-error {
  color: var(--ui-error);
  background: var(--ui-danger-soft);
}
.preview-info {
  color: var(--ui-info);
  background: var(--ui-info-soft);
}
.preview-plan {
  color: var(--ui-purple);
  background: var(--ui-purple-soft);
}
.preview-dialog label {
  display: block;
  font-size: var(--ui-font-small);
}
.preview-dialog input {
  display: block;
  box-sizing: border-box;
  width: 100%;
  min-height: var(--ui-control-height);
  margin-block: 8px 12px;
  padding: 8px;
  border: 1px solid var(--ui-border-strong);
  border-radius: var(--ui-radius-control);
  background: var(--ui-bg);
  color: var(--ui-text);
  font: inherit;
}
.preview-actions {
  justify-content: flex-end;
}
.preview-dropdown {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
  padding: 8px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-row);
  background: var(--ui-popover);
}
</style>
