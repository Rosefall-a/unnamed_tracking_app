<script setup lang="ts">
// The anime edit form. The form itself is shared with movies and TV shows (see
// MediaFormModal); this keeps the props and events the anime page uses.
import MediaFormModal from "./MediaFormModal.vue";
import type { Anime } from "../types/anime";

defineProps<{
  show?: Anime | null;
}>();

const emit = defineEmits<{
  saved: [show: Anime];
  deleted: [showId: string];
  closed: [];
}>();
</script>

<template>
  <MediaFormModal
    kind="anime"
    :item="show"
    @saved="(item) => emit('saved', item as Anime)"
    @deleted="(id) => emit('deleted', id)"
    @closed="emit('closed')"
  />
</template>
