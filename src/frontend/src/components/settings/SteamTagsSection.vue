<script setup lang="ts">
// Steam's own genres are broad (Elden Ring is only Action and RPG). Its
// players also vote on tags like Souls-like, Open World and Dark Fantasy, which
// describe a game much better. This turns that on (it is on by default), and
// can re-read the tags of the Steam games already in the library.
import { ref, onMounted } from "vue";
import ToggleButton from "./ToggleButton.vue";
import { fetchPreferences, queuePreferences } from "../../services/preferences";
import { refreshSteamTags } from "../../services/librarySync";
import { preferences as sharedPreferences } from "../../state/preferences";
import {
  addFeedItem,
  completeTask,
  errorTask,
  startTask,
  updateTask,
} from "../../state/taskProgress";

const enabled = ref(true);
const error = ref<string | null>(null);
const savedNote = ref("");

onMounted(async () => {
  try {
    enabled.value = (await fetchPreferences()).steam_user_tags;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to load settings.";
  }
});

async function change(next: boolean) {
  const previous = enabled.value;
  enabled.value = next;
  error.value = null;
  try {
    const { prefs, latest } = await queuePreferences({ steam_user_tags: next });
    if (latest) {
      enabled.value = prefs.steam_user_tags;
      sharedPreferences.value = prefs;
    }
    savedNote.value = "Saved";
    setTimeout(() => (savedNote.value = ""), 1500);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save.";
    enabled.value = previous;
  }
}

// ---- update the games already in the library, a few at a time ----
const running = ref(false);

async function updateNow() {
  if (running.value) return;
  running.value = true;
  error.value = null;
  const task = startTask("Updating Steam genres", 1, { indeterminate: true });
  let offset = 0;
  let updated = 0;
  try {
    for (;;) {
      const batch = await refreshSteamTags(offset);
      updated += batch.updated;
      offset += batch.processed;
      updateTask(task, offset, batch.total);
      if (batch.updated)
        addFeedItem(task, `${updated} game${updated === 1 ? "" : "s"} updated`);
      if (batch.done || !batch.processed) {
        completeTask(
          task,
          `${updated} of ${batch.total} Steam game${batch.total === 1 ? "" : "s"} updated`,
        );
        break;
      }
    }
  } catch (e) {
    const message = e instanceof Error ? e.message : "Failed to update.";
    errorTask(task, message);
    error.value = message;
  } finally {
    running.value = false;
  }
}
</script>

<template>
  <section class="settings-section steam-tags">
    <h2>Steam tags as genres</h2>
    <p class="section-hint">
      Steam's own genres are broad: Elden Ring is only Action and RPG. Its
      players also vote on tags like Souls-like, Open World, Dark Fantasy and
      Difficult, which say much more. With this on, a Steam game's genres are
      its most voted tags, without the ones that are not genres (Singleplayer,
      Co-op, Controller support, Great Soundtrack and similar), plus its
      official genres. It applies when a Steam game is added or its metadata is
      refreshed.
      <span v-if="savedNote" class="saved">{{ savedNote }}</span>
    </p>
    <ToggleButton
      :model-value="enabled"
      label="Use popular Steam tags as genres"
      @update:model-value="change"
    >
      <strong>Use popular Steam tags as genres</strong>
    </ToggleButton>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="update-row">
      <button
        type="button"
        class="ui-btn ui-btn-secondary"
        :disabled="running"
        @click="updateNow"
      >
        {{ running ? "Updating…" : "Update my Steam games now" }}
      </button>
      <span class="update-hint"
        >Re-reads the tags of the Steam games already in your library. It reads
        one store page a second, so a large library takes a few minutes. Tags
        you added yourself are kept.</span
      >
    </div>
  </section>
</template>

<style scoped>
.steam-tags {
  margin-top: 36px;
}
.settings-section h2 {
  margin: 0 0 8px;
  padding-left: 12px;
  border-left: 3px solid var(--ui-accent-text);
  font-size: 1rem;
  color: var(--ui-text);
}
.section-hint {
  color: var(--ui-dim);
  font-size: 0.82rem;
  line-height: 1.6;
  margin: 0 0 16px;
}
.saved {
  margin-left: 8px;
  color: var(--ui-accent-text);
  font-weight: 700;
}
.error {
  color: var(--ui-error);
  font-size: 0.85rem;
}
.update-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 16px;
}
.update-hint {
  color: var(--ui-faint);
  font-size: 0.78rem;
  line-height: 1.5;
  max-width: 460px;
}
</style>
