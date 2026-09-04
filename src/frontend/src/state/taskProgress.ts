import { reactive } from 'vue'

export type TaskStatus = 'running' | 'done' | 'error'

export interface ProgressTask {
  id: string
  label: string
  done: number
  total: number
  status: TaskStatus
  detail?: string
}

// Global, App-level store — deliberately outside any page/section component
// so a task's progress survives switching Settings tabs (which unmounts the
// section that started it) or navigating elsewhere entirely.
export const tasks = reactive<ProgressTask[]>([])

export function startTask(label: string, total: number): string {
  const id = crypto.randomUUID()
  tasks.push({ id, label, done: 0, total, status: 'running' })
  return id
}

export function updateTask(id: string, done: number) {
  const task = tasks.find((t) => t.id === id)
  if (task) task.done = done
}

export function completeTask(id: string, detail?: string) {
  const task = tasks.find((t) => t.id === id)
  if (task) {
    task.status = 'done'
    task.done = task.total
    if (detail) task.detail = detail
  }
}

export function errorTask(id: string, detail?: string) {
  const task = tasks.find((t) => t.id === id)
  if (task) {
    task.status = 'error'
    if (detail) task.detail = detail
  }
}

export function dismissTask(id: string) {
  const index = tasks.findIndex((t) => t.id === id)
  if (index !== -1) tasks.splice(index, 1)
}
