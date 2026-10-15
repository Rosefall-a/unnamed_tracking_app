<script setup lang="ts">
// The movie edit form. The form itself is shared with TV shows and anime (see
// MediaFormModal); this keeps the props and events the movie page uses.
import MediaFormModal from "./MediaFormModal.vue";
import type { Movie } from "../types/movie";

defineProps<{
  movie?: Movie | null;
}>();

const emit = defineEmits<{
  saved: [movie: Movie];
  deleted: [movieId: string];
  closed: [];
}>();
</script>

<template>
  <MediaFormModal
    kind="movie"
    :item="movie"
    @saved="(item) => emit('saved', item as Movie)"
    @deleted="(id) => emit('deleted', id)"
    @closed="emit('closed')"
  />
</template>
