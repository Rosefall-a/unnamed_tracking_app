import { reactive } from "vue";

export type TaskStatus = "running" | "done" | "error";

export interface ProgressTask {
  id: string;
  label: string;
  done: number;
  total: number;
  status: TaskStatus;
  detail?: string;
  // true when `done`/`total` don't mean anything yet (e.g. a single bulk
  // request with no per-item signal until it resolves), the toast shows
  // a scanning bar instead of a fraction
  indeterminate?: boolean;
  // e.g. "4.2 MB/s · 12s left", set from a real XHR upload-progress event
  // (see utils/uploadSpeed.ts), not shown until there's an actual reading
  speedLabel?: string;
  // set when a failed task can be retried without re-selecting the file(s)
  //, re-runs the exact same upload attempt (see setTaskRetry)
  retry?: () => void;
  // individual items as they complete, rendered as a small scrolling feed
  // under the progress bar (e.g. "Cyberpunk 2077 imported"). Each entry
  // carries its own stable id, keying the rendered list off its position
  // in a growing/slicing array meant every entry's key changed on every
  // push, so Vue tore down and re-mounted the whole feed on each new item
  // instead of animating just the new line in.
  feed: FeedEntry[];
}

export interface FeedEntry {
  id: string;
  text: string;
}

// `crypto.randomUUID()` is only exposed in secure browser contexts. The app
// can be served over plain HTTP on a local network, where `crypto` exists but
// `randomUUID` does not. `getRandomValues` is available there, so use it to
// generate RFC 4122 v4 ids without requiring HTTPS just for task tracking.
function createId(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();

  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;

  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0"));
  return [
    hex.slice(0, 4).join(""),
    hex.slice(4, 6).join(""),
    hex.slice(6, 8).join(""),
    hex.slice(8, 10).join(""),
    hex.slice(10, 16).join(""),
  ].join("-");
}

// Global, App-level store, deliberately outside any page/section component
// so a task's progress survives switching Settings tabs (which unmounts the
// section that started it) or navigating elsewhere entirely.
export const tasks = reactive<ProgressTask[]>([]);

export function startTask(
  label: string,
  total: number,
  options: { indeterminate?: boolean } = {},
): string {
  const id = createId();
  tasks.push({
    id,
    label,
    done: 0,
    total,
    status: "running",
    feed: [],
    indeterminate: options.indeterminate,
  });
  return id;
}

export function updateTask(
  id: string,
  done: number,
  total?: number,
  speedLabel?: string,
) {
  const task = tasks.find((t) => t.id === id);
  if (task) {
    task.done = done;
    if (total !== undefined) task.total = total;
    if (speedLabel !== undefined) task.speedLabel = speedLabel;
  }
}

// appends one line to the task's completion feed, called as each
// individual item (a file, a game) finishes, not just at the end
export function addFeedItem(id: string, text: string) {
  const task = tasks.find((t) => t.id === id);
  if (task) task.feed.push({ id: createId(), text });
}

// success toasts clear themselves out after a bit so they don't pile up,
// errors are left for a manual dismiss (state/taskProgress.ts's errorTask)
// since those are worth actually noticing, not auto-hiding
const AUTO_DISMISS_MS = 6000;

export function completeTask(id: string, detail?: string) {
  const task = tasks.find((t) => t.id === id);
  if (task) {
    task.status = "done";
    task.done = task.total;
    if (detail) task.detail = detail;
  }
  setTimeout(() => dismissTask(id), AUTO_DISMISS_MS);
}

export function errorTask(id: string, detail?: string) {
  const task = tasks.find((t) => t.id === id);
  if (task) {
    task.status = "error";
    if (detail) task.detail = detail;
  }
}

// lets a failed upload retry the exact same file(s) with one click instead
// of forcing the user back to the dropzone, a network blip on a large
// world save shouldn't mean starting the whole upload over from scratch
export function setTaskRetry(id: string, retry: () => void) {
  const task = tasks.find((t) => t.id === id);
  if (task) task.retry = retry;
}

export function dismissTask(id: string) {
  const index = tasks.findIndex((t) => t.id === id);
  if (index !== -1) tasks.splice(index, 1);
}
