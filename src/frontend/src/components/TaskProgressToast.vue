<script setup lang="ts">
import { tasks, dismissTask } from "../state/taskProgress";

function retry(task: (typeof tasks)[number]) {
  task.retry?.();
  task.status = "running";
  task.detail = undefined;
  task.done = 0;
}

function percent(done: number, total: number): number {
  if (total <= 0) return 0;
  return Math.min(100, Math.round((done / total) * 100));
}
</script>

<template>
  <Teleport to="body">
    <div v-if="tasks.length" class="task-toast-stack">
      <div
        v-for="task in tasks"
        :key="task.id"
        class="task-toast"
        :class="task.status"
      >
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
          <div
            class="task-toast-fill"
            :class="{
              indeterminate: task.indeterminate && task.status === 'running',
            }"
            :style="
              task.indeterminate
                ? {}
                : { width: percent(task.done, task.total) + '%' }
            "
          ></div>
        </div>
        <div class="task-toast-meta">
          <span v-if="task.status === 'running'">
            {{
              task.indeterminate ? "Working…" : `${task.done} / ${task.total}`
            }}
            <span v-if="task.speedLabel" class="task-toast-speed"
              >· {{ task.speedLabel }}</span
            >
          </span>
          <span v-else-if="task.status === 'done'">{{
            task.detail || "Done"
          }}</span>
          <span v-else class="task-toast-error">{{
            task.detail || "Failed"
          }}</span>
        </div>
        <button
          v-if="task.status === 'error' && task.retry"
          type="button"
          class="task-toast-retry"
          @click="retry(task)"
        >
          Retry
        </button>
        <div v-if="task.feed.length" class="task-toast-feed">
          <TransitionGroup
            name="feed-item"
            tag="div"
            class="task-toast-feed-inner"
          >
            <div
              v-for="entry in task.feed.slice(-6)"
              :key="entry.id"
              class="feed-line"
            >
              {{ entry.text }}
            </div>
          </TransitionGroup>
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
.task-toast-fill.indeterminate {
  width: 40% !important;
  animation: task-toast-scan 1.1s ease-in-out infinite;
}
@keyframes task-toast-scan {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(250%);
  }
}
.task-toast-meta {
  font-size: 0.76rem;
  color: #999;
}
.task-toast-error {
  color: #fca5a5;
}
.task-toast-speed {
  color: #777;
}
.task-toast-retry {
  margin-top: 8px;
  background: rgba(220, 38, 38, 0.12);
  border: 1px solid rgba(220, 38, 38, 0.35);
  color: #fca5a5;
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 0.76rem;
  cursor: pointer;
}
.task-toast-retry:hover {
  background: rgba(220, 38, 38, 0.2);
}
.task-toast-feed {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #232323;
  /* bounded by task.feed.slice(-6) in the template, not by clipping height
     here: a fixed max-height + overflow:hidden was cutting lines off
     mid-character whenever the real rendered height came out a few pixels
     taller than the guessed value (padding/gap rounding, font metrics) */
}
.task-toast-feed-inner {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.feed-line {
  font-size: 0.72rem;
  line-height: 1.4;
  color: #aaa;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.feed-item-enter-active {
  transition:
    opacity 0.25s ease,
    transform 0.25s ease;
}
.feed-item-enter-from {
  opacity: 0;
  transform: translateY(4px);
}
</style>
