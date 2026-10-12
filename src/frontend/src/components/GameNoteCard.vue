<script setup lang="ts">
// One note on a card: its name, the start of its text, the achievement and tags
// it carries, its checklist progress and its dates. The Notes tab and an
// achievement's own page show notes with this one card. The tab passes its pin
// and menu buttons in; a page that only shows the note passes none.
import type { GameNoteSummary } from "../services/games";
import { dates, excerpt, wordLabel } from "../utils/noteDisplay";

defineProps<{ note: GameNoteSummary; achievementName?: string | null }>();
const emit = defineEmits<{ open: [] }>();
</script>

<template>
  <article
    class="np-card"
    :class="{ pinned: note.pinned }"
    tabindex="0"
    @click="emit('open')"
    @keydown.enter="emit('open')"
  >
    <header class="np-card-top">
      <h3 class="np-card-title">{{ note.name }}</h3>
      <div v-if="$slots.buttons" class="np-card-btns" @click.stop>
        <slot name="buttons" />
      </div>
    </header>
    <p class="np-card-excerpt">{{ excerpt(note.preview) || "Empty note" }}</p>
    <div v-if="note.tags.length || achievementName" class="np-card-chips">
      <span v-if="achievementName" class="np-chip ach">
        <svg
          viewBox="0 0 24 24"
          width="11"
          height="11"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M8 4h8v5a4 4 0 0 1-8 0z" />
          <path d="M8 4H5a2 2 0 0 0 0 4h1.5M16 4h3a2 2 0 0 1 0 4h-1.5" />
          <path d="M12 13v3" />
          <path d="M9 20h6" />
          <path d="M10 16.5h4l.8 3.5H9.2z" />
        </svg>
        {{ achievementName }}
      </span>
      <span v-for="t in note.tags.slice(0, 3)" :key="t" class="np-chip">{{
        t
      }}</span>
      <span v-if="note.tags.length > 3" class="np-chip"
        >+{{ note.tags.length - 3 }}</span
      >
    </div>
    <div
      v-if="note.tasks_total"
      class="np-progress"
      :title="`${note.tasks_done} of ${note.tasks_total} done`"
    >
      <span class="np-progress-bar"
        ><span
          :style="{ width: `${(note.tasks_done / note.tasks_total) * 100}%` }"
        ></span
      ></span>
      <span class="np-progress-n"
        >{{ note.tasks_done }}/{{ note.tasks_total }}</span
      >
    </div>
    <footer class="np-card-foot">
      <span>{{ dates(note) }}</span>
      <span>{{ wordLabel(note.words) }}</span>
    </footer>
  </article>
</template>

<style scoped src="./GameNotesPanel.css"></style>
