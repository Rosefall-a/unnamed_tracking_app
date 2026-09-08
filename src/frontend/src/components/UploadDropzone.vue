<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(
  defineProps<{
    accept?: string
    multiple?: boolean
    uploading?: boolean
    title?: string
    hint?: string
  }>(),
  {
    accept: '*/*',
    multiple: true,
    uploading: false,
    title: 'Drop files here',
    hint: 'Drag and drop, or click to browse',
  },
)

const emit = defineEmits<{
  'files-selected': [files: File[]]
  'drop-error': [message: string]
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const dragging = ref(false)
let dragDepth = 0

function onDragEnter(e: DragEvent) {
  e.preventDefault()
  dragDepth++
  dragging.value = true
}
function onDragOver(e: DragEvent) {
  e.preventDefault()
}
function onDragLeave(e: DragEvent) {
  e.preventDefault()
  dragDepth = Math.max(0, dragDepth - 1)
  if (dragDepth === 0) dragging.value = false
}
function onDrop(e: DragEvent) {
  e.preventDefault()
  dragDepth = 0
  dragging.value = false

  // Dropping a folder (not a file) is a real, easy mistake here, e.g. a
  // Minecraft world save's own folder, un-zipped, and some browsers
  // return it via dataTransfer.files as a 0-byte/empty entry, or omit it
  // from .files entirely. Either way the drop silently did nothing before
  // this check: no request, no error, nothing. webkitGetAsEntry is
  // non-standard in name only, Chrome/Edge/Firefox/Safari all support it.
  const items = e.dataTransfer?.items
  if (items?.length) {
    for (const item of Array.from(items)) {
      const entry = (item as DataTransferItem & { webkitGetAsEntry?: () => { isDirectory?: boolean } | null })
        .webkitGetAsEntry?.()
      if (entry?.isDirectory) {
        emit('drop-error', "That's a folder: zip it first, then drop the .zip file here.")
        return
      }
    }
  }

  const files = Array.from(e.dataTransfer?.files ?? [])
  if (files.length) {
    emit('files-selected', files)
  } else if (items?.length) {
    emit('drop-error', 'Could not read what was dropped: try dropping the file(s) directly.')
  }
}
function onClick() {
  if (!props.uploading) inputRef.value?.click()
}
function onInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  if (files.length) emit('files-selected', files)
  input.value = ''
}
</script>

<template>
  <div
    class="dropzone"
    :class="{ dragging, uploading }"
    @dragenter="onDragEnter"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
    @click="onClick"
  >
    <svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" class="dropzone-icon">
      <path d="M12 13v8" />
      <path d="M8.5 16.5 12 13l3.5 3.5" />
      <path d="M20 17.58A5 5 0 0 0 18 8h-1.26A8 8 0 1 0 4 15.25" />
    </svg>
    <div class="dropzone-title">{{ uploading ? 'Uploading…' : title }}</div>
    <div class="dropzone-hint">{{ hint }}</div>
    <input ref="inputRef" type="file" :accept="accept" :multiple="multiple" class="hidden-input" :disabled="uploading" @change="onInputChange" />
  </div>
</template>

<style scoped>
.dropzone {
  border: 2px dashed #3a3a3a;
  border-radius: 12px;
  padding: 36px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.02);
  transition: border-color 0.15s ease, background 0.15s ease;
}
.dropzone:hover {
  border-color: #d68a34;
  background: rgba(214, 138, 52, 0.04);
}
.dropzone.dragging {
  border-color: #d68a34;
  background: rgba(214, 138, 52, 0.08);
}
.dropzone.uploading {
  cursor: wait;
  opacity: 0.7;
}
.dropzone-icon {
  color: #d68a34;
}
.dropzone-title {
  color: #fff;
  font-weight: 600;
  font-size: 0.95rem;
}
.dropzone-hint {
  color: #777;
  font-size: 0.78rem;
}
.hidden-input {
  display: none;
}
</style>
