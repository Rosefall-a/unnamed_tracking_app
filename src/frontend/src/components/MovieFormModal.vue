<script setup lang="ts">
import { ref, watch } from "vue";
import { createMovie, updateMovie, deleteMovie } from "../services/movies";
import type { Movie, MovieStatus } from "../types/movie";

const props = defineProps<{
  movie?: Movie | null;
}>();

const emit = defineEmits<{
  saved: [movie: Movie];
  deleted: [movieId: string];
  closed: [];
}>();

const STATUSES: MovieStatus[] = [
  "wishlist",
  "watchlist",
  "backlog",
  "in progress",
  "watched",
  "rewatch",
  "favorite",
  "dropped",
];

function blankFields() {
  return {
    title: "",
    description: "",
    releaseDate: "",
    runtimeMinutes: null as number | null,
    director: "",
    writer: "",
    studiosInput: "",
    genresInput: "",
    tagsInput: "",
    status: "wishlist" as MovieStatus,
    favorite: false,
    ratingOverall: null as number | null,
    personalRank: null as number | null,
  };
}

const fields = ref(blankFields());
const saving = ref(false);
const deleting = ref(false);
const error = ref<string | null>(null);

function loadFromMovie(movie: Movie | null | undefined) {
  if (!movie) {
    fields.value = blankFields();
    return;
  }
  fields.value = {
    title: movie.title,
    description: movie.description ?? "",
    releaseDate: movie.releaseDate ?? "",
    runtimeMinutes: movie.runtimeMinutes,
    director: movie.director ?? "",
    writer: movie.writer ?? "",
    studiosInput: movie.studios.join(", "),
    genresInput: movie.genres.join(", "),
    tagsInput: movie.tags.join(", "),
    status: movie.status,
    favorite: movie.favorite,
    ratingOverall: movie.ratingOverall,
    personalRank: movie.personalRank,
  };
}

watch(() => props.movie, loadFromMovie, { immediate: true });

function splitList(input: string): string[] {
  return input
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

async function submit() {
  if (!fields.value.title.trim()) {
    error.value = "Title is required.";
    return;
  }
  saving.value = true;
  error.value = null;
  try {
    const input = {
      title: fields.value.title.trim(),
      description: fields.value.description.trim() || null,
      releaseDate: fields.value.releaseDate || null,
      runtimeMinutes: fields.value.runtimeMinutes,
      director: fields.value.director.trim() || null,
      writer: fields.value.writer.trim() || null,
      studios: splitList(fields.value.studiosInput),
      genres: splitList(fields.value.genresInput),
      tags: splitList(fields.value.tagsInput),
      status: fields.value.status,
      favorite: fields.value.favorite,
      ratingOverall: fields.value.ratingOverall,
      personalRank: fields.value.personalRank,
    };
    const saved = props.movie
      ? await updateMovie(props.movie.id, input)
      : await createMovie(input);
    emit("saved", saved);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to save movie.";
  } finally {
    saving.value = false;
  }
}

async function remove() {
  if (!props.movie) return;
  deleting.value = true;
  error.value = null;
  try {
    await deleteMovie(props.movie.id);
    emit("deleted", props.movie.id);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed to delete movie.";
  } finally {
    deleting.value = false;
  }
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('closed')">
    <div class="modal" role="dialog" aria-label="Movie">
      <div class="modal-head">
        <h2>{{ movie ? "Edit Movie" : "Add Movie" }}</h2>
        <button type="button" class="close-btn" @click="emit('closed')">
          &times;
        </button>
      </div>

      <div class="modal-body">
        <p v-if="error" class="error-text">{{ error }}</p>

        <label class="field">
          <span>Title</span>
          <input
            v-model="fields.title"
            type="text"
            class="text-input"
            placeholder="The Matrix"
          />
        </label>

        <label class="field">
          <span>Description</span>
          <textarea
            v-model="fields.description"
            class="text-input textarea-input"
            rows="3"
          ></textarea>
        </label>

        <div class="field-row">
          <label class="field">
            <span>Release date</span>
            <input
              v-model="fields.releaseDate"
              type="date"
              class="text-input"
            />
          </label>
          <label class="field">
            <span>Runtime (minutes)</span>
            <input
              v-model.number="fields.runtimeMinutes"
              type="number"
              min="0"
              class="text-input"
            />
          </label>
        </div>

        <div class="field-row">
          <label class="field">
            <span>Director</span>
            <input v-model="fields.director" type="text" class="text-input" />
          </label>
          <label class="field">
            <span>Writer</span>
            <input v-model="fields.writer" type="text" class="text-input" />
          </label>
        </div>

        <label class="field">
          <span>Studios (comma-separated)</span>
          <input v-model="fields.studiosInput" type="text" class="text-input" />
        </label>

        <label class="field">
          <span>Genres (comma-separated)</span>
          <input v-model="fields.genresInput" type="text" class="text-input" />
        </label>

        <label class="field">
          <span>Tags (comma-separated)</span>
          <input v-model="fields.tagsInput" type="text" class="text-input" />
        </label>

        <div class="field-row">
          <label class="field">
            <span>Status</span>
            <select v-model="fields.status" class="text-input">
              <option v-for="s in STATUSES" :key="s" :value="s">
                {{ s }}
              </option>
            </select>
          </label>
          <label class="field">
            <span>Overall rating (0-10)</span>
            <input
              v-model.number="fields.ratingOverall"
              type="number"
              min="0"
              max="10"
              step="0.1"
              class="text-input"
            />
          </label>
        </div>

        <div class="field-row">
          <label class="field checkbox-field">
            <input v-model="fields.favorite" type="checkbox" />
            <span>Favorite</span>
          </label>
          <label class="field">
            <span>Personal rank</span>
            <input
              v-model.number="fields.personalRank"
              type="number"
              min="1"
              class="text-input"
            />
          </label>
        </div>
      </div>

      <div class="modal-foot">
        <button
          v-if="movie"
          type="button"
          class="delete-btn"
          :disabled="deleting || saving"
          @click="remove"
        >
          {{ deleting ? "Deleting…" : "Delete" }}
        </button>
        <div class="modal-foot-spacer"></div>
        <button type="button" class="secondary-button" @click="emit('closed')">
          Cancel
        </button>
        <button
          type="button"
          class="primary-btn"
          :disabled="saving || deleting"
          @click="submit"
        >
          {{ saving ? "Saving…" : movie ? "Save Changes" : "Add Movie" }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(8, 6, 4, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.modal {
  width: 100%;
  max-width: 480px;
  max-height: 86vh;
  display: flex;
  flex-direction: column;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 30px 70px -20px rgba(0, 0, 0, 0.8);
  color: #fff;
  font-family: system-ui, sans-serif;
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 1px solid #2a2a2a;
}
.modal-head h2 {
  margin: 0;
  font-size: 1.05rem;
}
.close-btn {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  padding: 4px;
  font-size: 1.2rem;
  line-height: 1;
}
.close-btn:hover {
  color: #d68a34;
}
.modal-body {
  padding: 18px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.error-text {
  color: #fca5a5;
  font-size: 0.85rem;
  margin: 0;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
  min-width: 0;
}
.field span {
  font-size: 0.78rem;
  color: #999;
}
.field-row {
  display: flex;
  gap: 12px;
}
.checkbox-field {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}
.checkbox-field span {
  font-size: 0.85rem;
  color: #fff;
}
.text-input {
  background: #111;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  color: #fff;
  padding: 8px 10px;
  font-size: 0.85rem;
  font-family: inherit;
  width: 100%;
  box-sizing: border-box;
}
.text-input:focus {
  outline: 2px solid #d68a34;
  outline-offset: 1px;
}
.textarea-input {
  resize: vertical;
  min-height: 60px;
}
.modal-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 18px;
  border-top: 1px solid #2a2a2a;
}
.modal-foot-spacer {
  flex: 1;
}
.primary-btn {
  background: #d68a34;
  color: #121212;
  border: none;
  border-radius: 8px;
  padding: 9px 18px;
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
}
.primary-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.secondary-button {
  background: #111;
  border: 1px solid #2a2a2a;
  color: #ccc;
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 0.85rem;
  cursor: pointer;
}
.delete-btn {
  background: none;
  border: 1px solid #5c2a2a;
  color: #fca5a5;
  border-radius: 8px;
  padding: 9px 14px;
  font-size: 0.85rem;
  cursor: pointer;
}
.delete-btn:hover {
  background: #2a1414;
}
.delete-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
