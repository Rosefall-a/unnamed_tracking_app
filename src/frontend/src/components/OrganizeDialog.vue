<script setup lang="ts">
// Set games aside (or bring them back): one game from its card menu, or every
// game picked with Select. Nothing is deleted.
import { computed, ref } from "vue";
import { bulkUpdateGames } from "../services/gameBulk";
import type { Game, SetAsideReason } from "../types/game";
import { SET_ASIDE_REASONS, isSetAside } from "../utils/gameOrganize";

const props = defineProps<{
  games: Game[];
}>();
const emit = defineEmits<{
  close: [];
  // the fields every one of these games now has, so the library can follow
  saved: [
    ids: string[],
    fields: {
      setAsideAt?: string | null;
      setAsideReason?: SetAsideReason | null;
    },
  ];
}>();

const count = computed(() => props.games.length);
const what = computed(() =>
  count.value === 1 ? `"${props.games[0].title}"` : `${count.value} games`,
);
const allAside = computed(() => props.games.every(isSetAside));
const reason = ref<SetAsideReason>(
  props.games[0]?.setAsideReason ?? "not_a_game",
);
const saving = ref(false);
const error = ref<string | null>(null);

async function save(fields: Parameters<typeof bulkUpdateGames>[1]) {
  saving.value = true;
  error.value = null;
  try {
    const ids = props.games.map((g) => g.id);
    await bulkUpdateGames(ids, fields);
    emit("saved", ids, {
      setAsideAt: fields.setAside ? new Date().toISOString() : null,
      setAsideReason: fields.setAside ? (fields.setAsideReason ?? null) : null,
    });
    emit("close");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Could not save that.";
  } finally {
    saving.value = false;
  }
}
const setAside = () => save({ setAside: true, setAsideReason: reason.value });
const bringBack = () => save({ setAside: false });
</script>

<template>
  <div class="org-backdrop" @click.self="emit('close')">
    <div
      class="org-modal"
      role="dialog"
      aria-modal="true"
      aria-label="Set aside"
      @keydown.esc="emit('close')"
    >
      <h3>Set aside {{ what }}</h3>
      <p class="org-lead">
        Kept with everything it has (status, achievements, files), but out of
        your library tabs, Home and counts. Find it again under the Set aside
        tab.
      </p>
      <div class="org-options">
        <label
          v-for="r in SET_ASIDE_REASONS"
          :key="r.id"
          class="org-option"
          :class="{ on: reason === r.id }"
        >
          <input v-model="reason" type="radio" name="reason" :value="r.id" />
          <span>
            <b>{{ r.label }}</b>
            <small>{{ r.hint }}</small>
          </span>
        </label>
      </div>
      <p v-if="error" class="ui-error-box">{{ error }}</p>
      <div class="org-actions">
        <button
          v-if="props.games.some(isSetAside)"
          type="button"
          class="ui-btn ui-btn-secondary"
          :disabled="saving"
          @click="bringBack"
        >
          {{ allAside ? "Bring back" : "Bring back the set-aside ones" }}
        </button>
        <span class="grow"></span>
        <button
          type="button"
          class="ui-btn ui-btn-secondary"
          @click="emit('close')"
        >
          Cancel
        </button>
        <button
          type="button"
          class="ui-btn ui-btn-primary"
          :disabled="saving"
          @click="setAside"
        >
          {{ saving ? "Saving…" : "Set aside" }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.org-backdrop {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: color-mix(in srgb, var(--ui-scrim-base) 60%, transparent);
}
.org-modal {
  width: min(480px, 100%);
  max-height: calc(100vh - 32px);
  overflow-y: auto;
  box-sizing: border-box;
  background: var(--ui-popover);
  border: 1px solid var(--ui-border-strong);
  border-radius: 14px;
  padding: 20px;
  box-shadow: 0 24px 60px
    color-mix(in srgb, var(--ui-scrim-base) 55%, transparent);
}
h3 {
  margin: 0;
  font-size: 1.05rem;
  color: var(--ui-heading);
}
.org-lead {
  margin: 6px 0 14px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--ui-dim);
}
.org-options {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.org-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--ui-border);
  border-radius: 10px;
  cursor: pointer;
}
.org-option:hover {
  border-color: var(--ui-border-strong);
}
.org-option.on {
  border-color: var(--ui-accent-line);
  background: color-mix(in srgb, var(--ui-accent) 8%, transparent);
}
.org-option input {
  margin-top: 3px;
  accent-color: var(--ui-accent);
}
.org-option b {
  display: block;
  font-size: 13.5px;
  color: var(--ui-heading);
}
.org-option small {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  color: var(--ui-dim-2);
}
.org-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
}
.grow {
  flex: 1;
}
</style>
