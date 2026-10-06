<script setup lang="ts">
import { computed, ref, nextTick, watch } from "vue";
import { useRoute } from "vue-router";
import { preferences } from "../../state/preferences";
import {
  keyboardShortcuts,
  shortcutDefinitions,
  shortcutBinding,
  type ShortcutOverride,
} from "../../state/shortcuts";
import {
  prepareShortcutOverride,
  reconcileShortcutOverrides,
} from "../../utils/shortcutResolution";
import { notifyShortcutConflicts } from "../../state/shortcutNotices";
import { queuePreferences, type Preferences } from "../../services/preferences";
import {
  normalizeShortcutKey,
  shortcutKeyLabel,
} from "../../utils/shortcutKeys";
import UiModal from "../UiModal.vue";

const saving = ref(false),
  message = ref(""),
  error = ref("");
const route = useRoute();
const selected = ref<string | null>(null),
  draft = ref<string[]>([]),
  recording = ref<number | null>(null);
const editing = computed(() =>
  selected.value ? shortcutBinding(selected.value) : undefined,
);
const groups = computed(() =>
  [...new Set(keyboardShortcuts.value.map((item) => item.group))].map(
    (title) => ({
      title,
      items: keyboardShortcuts.value.filter((item) => item.group === title),
    }),
  ),
);
const normalized = computed(() => draft.value.map(normalizeShortcutKey));
const valid = computed(
  () => normalized.value.length > 0 && normalized.value.every((key) => !!key),
);
const conflicts = computed(() => {
  if (!editing.value || !valid.value) return [];
  return (
    prepareShortcutOverride(
      shortcutDefinitions.value,
      preferences.value.keyboard_shortcut_overrides,
      editing.value.id,
      { enabled: true, keys: normalized.value as string[] },
    ).disabled.find((item) => item.id === editing.value?.id)?.conflicts ?? []
  );
});
async function save(changes: Partial<Preferences>) {
  saving.value = true;
  error.value = "";
  message.value = "";
  try {
    const result = await queuePreferences(changes);
    if (result.latest) preferences.value = result.prefs;
    message.value = "Shortcut preferences saved to your account.";
    return true;
  } catch {
    error.value =
      "Could not save shortcut preferences. Your previous bindings are still active. Try again.";
    return false;
  } finally {
    saving.value = false;
  }
}
function edit(id: string) {
  selected.value = id;
  draft.value = [...(shortcutBinding(id)?.keys ?? [])];
  recording.value = null;
}
let openedBinding = "";
watch(
  [() => route.query.binding, shortcutDefinitions],
  ([value]) => {
    const id = typeof value === "string" ? value : "";
    if (!id) openedBinding = "";
    if (id !== openedBinding && shortcutBinding(id)) {
      openedBinding = id;
      edit(id);
    }
  },
  { immediate: true },
);
async function startRecording(index: number) {
  recording.value = recording.value === index ? null : index;
  await nextTick();
  if (recording.value !== null)
    document.getElementById(`shortcut-key-${index}`)?.focus();
}
async function saveOverride(id: string, override?: ShortcutOverride) {
  const result = prepareShortcutOverride(
    shortcutDefinitions.value,
    preferences.value.keyboard_shortcut_overrides,
    id,
    override ?? { keys: undefined },
  );
  const saved = await save({ keyboard_shortcut_overrides: result.overrides });
  if (saved) notifyShortcutConflicts(result.disabled);
  return saved;
}
async function restoreDefaults() {
  const result = reconcileShortcutOverrides(shortcutDefinitions.value, {});
  if (
    await save({
      keyboard_shortcut_overrides: result.overrides,
      keyboard_shortcuts_enabled: true,
    })
  )
    notifyShortcutConflicts(result.disabled);
}
async function apply() {
  if (!editing.value || !valid.value) return;
  if (
    await saveOverride(editing.value.id, {
      ...preferences.value.keyboard_shortcut_overrides[editing.value.id],
      enabled: true,
      keys: normalized.value as string[],
    })
  )
    selected.value = null;
}
function record(event: KeyboardEvent, index: number) {
  if (recording.value !== index || event.key === "Escape") return;
  event.preventDefault();
  event.stopPropagation();
  if (
    ["Control", "Meta", "Alt", "Shift"].includes(event.key) ||
    event.isComposing ||
    event.getModifierState("AltGraph")
  )
    return;
  const key =
    event.altKey && /^Key[A-Z]$/.test(event.code)
      ? event.code.slice(3)
      : event.key === " "
        ? "Space"
        : event.key === "+"
          ? "Plus"
          : event.key;
  const combination = [
    ...(event.ctrlKey || event.metaKey ? ["CtrlOrMeta"] : []),
    ...(event.altKey ? ["Alt"] : []),
    ...(event.shiftKey && key !== "?" ? ["Shift"] : []),
    key,
  ].join("+");
  const value = normalizeShortcutKey(combination);
  if (value) {
    draft.value[index] = value;
    recording.value = null;
  }
}
</script>

<template>
  <div class="shortcut-bindings">
    <div class="master-controls">
      <label
        ><input
          type="checkbox"
          :checked="preferences.keyboard_shortcuts_enabled"
          :disabled="saving"
          @change="
            save({
              keyboard_shortcuts_enabled: ($event.target as HTMLInputElement)
                .checked,
            })
          "
        />Enable keyboard shortcuts</label
      >
      <button
        type="button"
        class="ui-btn ui-btn-ghost"
        :disabled="saving"
        @click="restoreDefaults"
      >
        Restore all defaults
      </button>
    </div>
    <p v-if="message" role="status" class="success">{{ message }}</p>
    <p v-if="error && !selected" role="alert" class="error">{{ error }}</p>
    <details
      v-for="(group, index) in groups"
      :key="group.title"
      :open="
        index === 0 ||
        group.items.some(
          (item) => item.id === selected || item.id === route.query.binding,
        )
      "
      class="binding-group"
    >
      <summary>
        {{ group.title }} <span>{{ group.items.length }} shortcuts</span>
      </summary>
      <article
        v-for="item in group.items"
        :key="item.id"
        class="binding"
        :data-shortcut-id="item.id"
      >
        <div class="binding-copy">
          <strong>{{ item.label }}</strong
          ><small v-if="item.pluginId">{{ item.pluginId }}</small>
          <p>
            <kbd v-for="key in item.keys" :key="key">{{
              shortcutKeyLabel(key)
            }}</kbd>
          </p>
          <p
            v-for="conflict in item.conflicts"
            :key="conflict.key"
            class="conflict"
            role="status"
          >
            {{ shortcutKeyLabel(conflict.key) }} conflicts with
            {{ conflict.label }}. This binding is disabled; the oldest enabled
            shortcut stays active.
          </p>
        </div>
        <div class="binding-controls">
          <label
            ><input
              type="checkbox"
              :checked="item.enabled"
              :disabled="saving"
              :aria-label="`Enable ${item.label}`"
              @change="
                saveOverride(item.id, {
                  ...preferences.keyboard_shortcut_overrides[item.id],
                  enabled: ($event.target as HTMLInputElement).checked,
                })
              "
            />Enabled</label
          ><button
            type="button"
            class="ui-btn ui-btn-ghost"
            :disabled="saving"
            :aria-label="`Change keys for ${item.label}`"
            @click="edit(item.id)"
          >
            Change keys
          </button>
        </div>
      </article>
    </details>
    <p class="hint">
      Tab, Enter, Space and Escape keep their normal control and dialog
      behavior. Extension shortcuts disappear when the extension stops; saved
      choices return when it is available again.
    </p>
  </div>
  <UiModal
    v-if="editing"
    :title="`Change shortcut: ${editing.label}`"
    description="Type a combination or record it. CtrlOrMeta uses Ctrl on Windows/Linux and Command on macOS. Add up to four alternatives."
    @close="selected = null"
  >
    <div class="binding-editor">
      <div v-for="(_, index) in draft" :key="index" class="key-editor">
        <label :for="`shortcut-key-${index}`"
          >Key combination {{ index + 1 }}</label
        >
        <div>
          <input
            :id="`shortcut-key-${index}`"
            class="ui-field"
            v-model="draft[index]"
            :readonly="recording === index"
            :placeholder="recording === index ? 'Press your keys…' : 'Alt+G'"
            @keydown="record($event, index)"
          /><button
            type="button"
            class="ui-btn ui-btn-ghost"
            @click="startRecording(index)"
          >
            {{ recording === index ? "Stop recording" : "Record keys" }}</button
          ><button
            v-if="draft.length > 1"
            type="button"
            class="ui-btn ui-btn-ghost"
            :aria-label="`Remove combination ${index + 1}`"
            @click="draft.splice(index, 1)"
          >
            Remove
          </button>
        </div>
      </div>
      <button
        v-if="draft.length < 4"
        type="button"
        class="ui-btn ui-btn-ghost"
        @click="draft.push('')"
      >
        Add alternative
      </button>
      <p v-if="!valid" class="error" role="status">
        Enter a single key, such as N, or a combination such as Alt+G or
        CtrlOrMeta+K.
      </p>
      <p
        v-for="conflict in conflicts"
        :key="conflict.key"
        class="conflict"
        role="status"
      >
        {{ shortcutKeyLabel(conflict.key) }} is used by {{ conflict.label }}.
        Saving these keys will leave this shortcut disabled. Remap it or disable
        the older binding before enabling this one.
      </p>
      <p v-if="error" role="alert" class="error">{{ error }}</p>
    </div>
    <template #footer
      ><button
        type="button"
        class="ui-btn ui-btn-ghost"
        :disabled="saving"
        @click="
          saveOverride(editing.id).then((saved) => {
            if (saved) selected = null;
          })
        "
      >
        Use default keys</button
      ><button
        type="button"
        class="ui-btn ui-btn-primary"
        :disabled="saving || !valid"
        @click="apply"
      >
        {{
          saving ? "Saving…" : editing.enabled ? "Save keys" : "Save & enable"
        }}
      </button></template
    >
  </UiModal>
</template>

<style scoped>
.shortcut-bindings,
.binding-editor {
  display: grid;
  gap: var(--ui-space-4);
}
.master-controls,
.binding-controls,
.key-editor > div {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--ui-space-3);
}
.master-controls {
  justify-content: space-between;
}
label {
  display: flex;
  align-items: center;
  gap: var(--ui-space-2);
  min-height: var(--ui-control-height);
}
input[type="checkbox"] {
  width: 20px;
  height: 20px;
  accent-color: var(--ui-accent);
}
.binding-group {
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-card);
  overflow: hidden;
}
summary {
  padding: var(--ui-space-4);
  background: var(--ui-surface-2);
  cursor: pointer;
  font-weight: var(--ui-weight-heading);
}
summary span {
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
  margin-left: var(--ui-space-3);
  font-weight: 400;
}
.binding {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--ui-space-4);
  padding: var(--ui-space-4);
}
.binding + .binding {
  border-top: 1px solid var(--ui-border);
}
.binding-copy {
  min-width: 0;
  overflow-wrap: anywhere;
}
.binding-copy small {
  display: block;
  color: var(--ui-dim);
  margin-top: var(--ui-space-1);
}
.binding-copy p {
  margin: var(--ui-space-2) 0 0;
}
kbd {
  display: inline-block;
  padding: 4px 8px;
  margin-right: var(--ui-space-2);
  border: 1px solid var(--ui-border-strong);
  border-radius: var(--ui-radius-control);
  background: var(--ui-surface-2);
  font-size: var(--ui-font-small);
}
.conflict {
  color: var(--ui-warning);
  background: var(--ui-warning-soft);
  border-left: 3px solid var(--ui-warning);
  padding: var(--ui-space-3);
  border-radius: var(--ui-radius-control);
  font-size: var(--ui-font-small);
  line-height: 1.5;
}
.error {
  color: var(--ui-error);
}
.success {
  color: var(--ui-success);
}
.hint {
  color: var(--ui-dim);
  font-size: var(--ui-font-small);
  line-height: 1.6;
}
.key-editor input {
  flex: 1;
  min-width: 120px;
}
@media (max-width: 620px) {
  .binding {
    grid-template-columns: 1fr;
  }
  .binding-controls {
    justify-content: space-between;
  }
}
</style>
