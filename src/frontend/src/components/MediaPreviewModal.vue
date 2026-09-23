<script setup lang="ts">
// Shown when a Related/Recommended title isn't in the user's own library
// yet — a lightweight look before committing to "Add to Library", reused
// across Movie/TV Show/Anime detail pages.
defineProps<{
  title: string;
  posterUrl: string | null;
  description: string | null;
  meta: string[];
  loading: boolean;
  adding: boolean;
  error: string | null;
}>();

const emit = defineEmits<{
  (e: "add"): void;
  (e: "close"): void;
}>();
</script>

<template>
  <div class="preview-overlay" @click.self="emit('close')">
    <div class="preview-modal">
      <button
        type="button"
        class="preview-close"
        title="Close"
        @click="emit('close')"
      >
        &times;
      </button>

      <p v-if="loading" class="preview-loading">Loading…</p>

      <template v-else>
        <div class="preview-body">
          <div
            class="preview-poster"
            :style="posterUrl ? { backgroundImage: `url(${posterUrl})` } : {}"
          >
            <span v-if="!posterUrl">{{ title }}</span>
          </div>
          <div class="preview-info">
            <h3 class="preview-title">{{ title }}</h3>
            <div v-if="meta.length" class="preview-meta">
              <span v-for="m in meta" :key="m">{{ m }}</span>
            </div>
            <p v-if="description" class="preview-description">
              {{ description }}
            </p>
            <p v-if="error" class="preview-error">{{ error }}</p>
            <button
              type="button"
              class="preview-add-btn"
              :disabled="adding"
              @click="emit('add')"
            >
              {{ adding ? "Adding…" : "+ Add to Library" }}
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.preview-modal {
  position: relative;
  width: 100%;
  max-width: 520px;
  background: #171717;
  border: 1px solid #2b2b2b;
  border-radius: 14px;
  padding: 22px;
}
.preview-close {
  position: absolute;
  top: 12px;
  right: 12px;
  background: none;
  border: none;
  color: #888;
  font-size: 1.3rem;
  cursor: pointer;
  line-height: 1;
  padding: 4px;
}
.preview-close:hover {
  color: #fff;
}
.preview-loading {
  color: #999;
  font-size: 0.85rem;
  text-align: center;
  padding: 30px 0;
}
.preview-body {
  display: flex;
  gap: 18px;
}
.preview-poster {
  width: 130px;
  aspect-ratio: 2 / 3;
  flex-shrink: 0;
  border-radius: 8px;
  background-size: cover;
  background-position: center;
  background-color: #222222;
  border: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  color: #666;
  text-align: center;
  padding: 8px;
}
.preview-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.preview-title {
  margin: 0 0 6px;
  font-size: 1.15rem;
  font-weight: 800;
}
.preview-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.preview-meta span {
  font-size: 0.74rem;
  color: #9c9c9c;
  background: #222222;
  border: 1px solid #2b2b2b;
  border-radius: 6px;
  padding: 3px 8px;
}
.preview-description {
  font-size: 0.84rem;
  color: #999;
  line-height: 1.6;
  margin: 0 0 14px;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.preview-error {
  color: #fca5a5;
  font-size: 0.82rem;
  margin: 0 0 10px;
}
.preview-add-btn {
  margin-top: auto;
  align-self: flex-start;
  background: #d68a34;
  color: #0d0d0d;
  border: none;
  border-radius: 8px;
  padding: 9px 18px;
  font-weight: 700;
  font-size: 0.86rem;
  cursor: pointer;
}
.preview-add-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
