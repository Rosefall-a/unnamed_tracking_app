<script setup lang="ts">
import { computed, ref } from "vue";
import UiModal from "../UiModal.vue";
import PluginField from "./PluginField.vue";
import {
  validateField,
  type UiHomeWidget,
  type UiValues,
} from "../../services/pluginUi";
import { widgetConfiguration } from "../../services/homeWidgets";

const props = defineProps<{
  widget: UiHomeWidget;
  saved: UiValues;
  busy: boolean;
  error: string | null;
}>();
const emit = defineEmits<{ close: []; save: [values: UiValues] }>();
const values = ref(
  widgetConfiguration(props.widget.configuration, props.saved),
);
const submitted = ref(false);
const errors = computed(() =>
  Object.fromEntries(
    props.widget.configuration.map((field) => [
      field.id,
      validateField(field, values.value[field.id]),
    ]),
  ),
);
function save() {
  submitted.value = true;
  if (Object.values(errors.value).some(Boolean)) return;
  emit("save", widgetConfiguration(props.widget.configuration, values.value));
}
</script>

<template>
  <UiModal
    :title="`Customize ${widget.title}`"
    description="These options are personal to your account."
    :dismissible="!busy"
    @close="emit('close')"
  >
    <p v-if="error" class="ui-alert" role="alert">{{ error }}</p>
    <form :id="`widget-config-${widget.id}`" @submit.prevent="save">
      <PluginField
        v-for="field in widget.configuration"
        :key="field.id"
        v-model="values[field.id]"
        :field="field"
        :disabled="busy"
        :error="submitted ? (errors[field.id] ?? undefined) : undefined"
      />
    </form>
    <template #footer>
      <button
        type="button"
        class="ui-btn ui-btn-ghost"
        :disabled="busy"
        @click="emit('close')"
      >
        Cancel
      </button>
      <button
        type="submit"
        :form="`widget-config-${widget.id}`"
        class="ui-btn ui-btn-primary"
        :disabled="busy"
      >
        {{ busy ? "Saving…" : "Save options" }}
      </button>
    </template>
  </UiModal>
</template>
