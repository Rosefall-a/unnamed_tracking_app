<script setup lang="ts">
import { computed } from "vue";
import DOMPurify from "dompurify";
import { marked } from "marked";

const props = defineProps<{ text: string }>();
const html = computed(() => {
  const fragment = DOMPurify.sanitize(
    marked.parse(props.text, { async: false }),
    {
      RETURN_DOM_FRAGMENT: true,
    },
  );
  // Package READMEs can reference repository images that are not shipped in
  // the archive. Keep their descriptions instead of requesting a host route.
  for (const image of fragment.querySelectorAll("img")) {
    if (/^https:\/\//i.test(image.getAttribute("src") ?? "")) continue;
    const caption = document.createElement("span");
    caption.textContent = `${image.alt || "Image"} (see publisher documentation)`;
    image.replaceWith(caption);
  }
  const container = document.createElement("div");
  container.append(fragment);
  return container.innerHTML;
});
</script>

<template>
  <article
    class="plugin-readme"
    aria-label="Plugin documentation"
    v-html="html"
  />
</template>

<style scoped>
.plugin-readme {
  min-width: 0;
  line-height: 1.65;
  overflow-wrap: anywhere;
}
.plugin-readme :deep(h1) {
  font-size: 1.5rem;
}
.plugin-readme :deep(h1),
.plugin-readme :deep(h2),
.plugin-readme :deep(h3) {
  color: var(--ui-text);
  margin: var(--ui-space-5) 0 var(--ui-space-3);
}
.plugin-readme :deep(p) {
  margin: var(--ui-space-3) 0;
}
.plugin-readme :deep(img) {
  max-width: 100%;
  height: auto;
}
.plugin-readme :deep(pre) {
  max-width: 100%;
  overflow: auto;
  padding: var(--ui-space-3);
  background: var(--ui-surface-2);
  border-radius: var(--ui-radius-control);
}
.plugin-readme :deep(table) {
  display: block;
  max-width: 100%;
  overflow: auto;
  border-collapse: collapse;
}
.plugin-readme :deep(td),
.plugin-readme :deep(th) {
  padding: var(--ui-space-2);
  border: 1px solid var(--ui-border);
  text-align: left;
}
</style>
