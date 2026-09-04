<script setup lang="ts">
import { tasks, dismissTask } from '../state/taskProgress'

function percent(done: number, total: number): number {
  if (total <= 0) return 0
  return Math.min(100, Math.round((done / total) * 100))
}
</script>

<template>
  <Teleport to="body">
    <div v-if="tasks.length" class="task-toast-stack">
      <div v-for="task in tasks" :key="task.id" class="task-toast" :class="task.status">
        <div class="task-toast-header">
          <span class="task-toast-label">{{ task.label }}</span>
          <button
            v-if="task.status !== 'running'"
            type="button"
            class="task-toast-dismiss"
            @click="dismissTask(task.id)"
          >
            ✕
          </button>
        </div>
        <div class="task-toast-track">
          <div class="task-toast-fill" :style="{ width: percent(task.done, task.total) + '%' }"></div>
        </div>
        <div class="task-toast-meta">
          <span v-if="task.status === 'running'">{{ task.done }} / {{ task.total }}</span>
          <span v-else-if="task.status === 'done'">{{ task.detail || 'Done' }}</span>
          <span v-else class="task-toast-error">{{ task.detail || 'Failed' }}</span>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.task-toast-stack {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 200;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 280px;
}
.task-toast {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  padding: 12px 14px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
}
.task-toast.done {
  border-color: rgba(34, 197, 94, 0.35);
}
.task-toast.error {
  border-color: rgba(220, 38, 38, 0.35);
}
.task-toast-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.task-toast-label {
  color: #fff;
  font-size: 0.82rem;
  font-weight: 600;
}
.task-toast-dismiss {
  background: none;
  border: none;
  color: #777;
  cursor: pointer;
  font-size: 12px;
  padding: 0;
}
.task-toast-dismiss:hover {
  color: #fff;
}
.task-toast-track {
  background: #111;
  border-radius: 6px;
  height: 8px;
  overflow: hidden;
  margin-bottom: 6px;
}
.task-toast-fill {
  background: #d68a34;
  height: 100%;
  transition: width 0.2s ease;
}
.task-toast.done .task-toast-fill {
  background: #4ade80;
}
.task-toast.error .task-toast-fill {
  background: #f87171;
}
.task-toast-meta {
  font-size: 0.76rem;
  color: #999;
}
.task-toast-error {
  color: #fca5a5;
}
</style>
