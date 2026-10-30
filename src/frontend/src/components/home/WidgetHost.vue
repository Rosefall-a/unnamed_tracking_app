<script setup lang="ts">
// Draws one widget: loads the data it asked for, works out whether to show
// examples (previews only, and only when this person has nothing of that kind),
// and turns a failed load into the frame's retry state.
import { computed, inject, onMounted, provide, watch } from "vue";
import WidgetFrame from "./WidgetFrame.vue";
import { CHROME_KEY, chromeFrom } from "../../home/chrome";
import { UPDATE_WIDGET, WIDGET_CONTEXT } from "../../home/context";
import { ensure, failed, isReady } from "../../home/data";
import { effectiveSettings } from "../../home/registry";
import type { WidgetDefinition } from "../../home/registry";

const props = defineProps<{
  // which widget on the page this is, so it can change its own settings
  id?: string;
  def: WidgetDefinition;
  settings: Record<string, unknown>;
  variant: string | null;
  w: number;
  h: number;
  // a preview in the gallery rather than a widget on the page
  preview?: boolean;
}>();

function load(force = false) {
  for (const key of [...props.def.needs, ...(props.def.soft ?? [])])
    void ensure(key, force);
}
onMounted(() => load());
watch(
  () => props.def.type,
  () => load(),
);

const loading = computed(() => props.def.needs.some((k) => !isReady(k)));
const error = computed(() => {
  for (const key of props.def.needs)
    if (failed.value[key]) return failed.value[key]!;
  return null;
});
const sample = computed(
  () => !!props.preview && !loading.value && !props.def.hasData(),
);
const merged = computed(() => effectiveSettings(props.def, props.settings));
provide(
  CHROME_KEY,
  computed(() => chromeFrom(merged.value)),
);

// lets the widget's own controls change its settings (not in the gallery)
const updateWidget = inject(UPDATE_WIDGET, null);
provide(
  WIDGET_CONTEXT,
  computed(() => {
    const id = props.id;
    if (!id || !updateWidget || props.preview) return null;
    return {
      id,
      def: props.def,
      settings: merged.value,
      variant: props.variant,
      w: props.w,
      h: props.h,
      update: (changes) =>
        updateWidget(id, { ...props.settings, ...changes }, props.variant),
      setVariant: (v) => updateWidget(id, props.settings, v),
    };
  }),
);
</script>

<template>
  <WidgetFrame
    v-if="error"
    :title="def.name"
    :error="error"
    @retry="load(true)"
  />
  <component
    :is="def.component"
    v-else
    :settings="merged"
    :variant="variant"
    :sample="sample"
    :loading="loading"
    :w="w"
    :h="h"
  />
</template>
