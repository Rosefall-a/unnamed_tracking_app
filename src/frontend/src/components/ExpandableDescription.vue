<script setup lang="ts">
// A page's description, cut to a few lines when it is long, with a
// Read more / Show less button.
import { computed, ref } from "vue";

const props = defineProps<{ text: string }>();

const expanded = ref(false);
const overflows = computed(() => props.text.length > 320);
</script>

<template>
  <div class="description-block">
    <p class="description" :class="{ clamped: overflows && !expanded }">
      {{ text }}
    </p>
    <button
      v-if="overflows"
      type="button"
      class="read-more-btn"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      {{ expanded ? "Show less" : "Read more" }}
    </button>
  </div>
</template>

<style scoped>
.description-block {
  margin-top: 22px;
}

.description {
  font-size: 0.96rem;
  line-height: 1.7;
  color: var(--ui-dim);
  margin: 0;
}

.description.clamped {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.read-more-btn {
  background: none;
  border: none;
  color: var(--ui-accent-text);
  font-family: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  padding: 6px 0 0;
}

.read-more-btn:hover {
  text-decoration: underline;
}
</style>
