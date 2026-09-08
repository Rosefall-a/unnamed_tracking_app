<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  modelValue: string
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [string]
}>()

const focused = ref(false)

// shows the first/last few characters and masks the middle, enough to
// recognize which key is saved at a glance without exposing the whole
// thing; the raw value is only ever shown while the field is focused
function mask(value: string): string {
  if (!value) return ''
  if (value.length <= 8) return '•'.repeat(value.length)
  return value.slice(0, 4) + '•'.repeat(Math.min(value.length - 8, 20)) + value.slice(-4)
}

const displayValue = computed(() => (focused.value ? props.modelValue : mask(props.modelValue)))

function onInput(event: Event) {
  emit('update:modelValue', (event.target as HTMLInputElement).value)
}
</script>

<template>
  <input
    :value="displayValue"
    type="text"
    autocomplete="off"
    autocapitalize="off"
    spellcheck="false"
    :placeholder="placeholder"
    @focus="focused = true"
    @blur="focused = false"
    @input="onInput"
  />
</template>
