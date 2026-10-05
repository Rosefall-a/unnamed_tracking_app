import { ref } from "vue";

export type SaveState = "idle" | "saving" | "saved" | "settled" | "error";

export const saveState = ref<SaveState>("idle");
export const savedAt = ref<number | null>(null);

let pending = 0;
let originalFetch: typeof window.fetch | null = null;
let generation = 0;
let batchFailed = false;
let confirmationTimer: ReturnType<typeof setTimeout> | null = null;

function clearConfirmation() {
  if (confirmationTimer !== null) clearTimeout(confirmationTimer);
  confirmationTimer = null;
}

function finishWrite(failed: boolean, currentGeneration: number) {
  if (generation !== currentGeneration) return;
  pending -= 1;
  batchFailed ||= failed;
  if (pending > 0) return;
  saveState.value = batchFailed ? "error" : "saved";
  if (batchFailed) return;
  savedAt.value = Date.now();
  confirmationTimer = setTimeout(() => {
    confirmationTimer = null;
    saveState.value = "settled";
  }, 12_000);
}

function isWrite(method: string | undefined): boolean {
  const m = (method ?? "GET").toUpperCase();
  return m === "POST" || m === "PUT" || m === "PATCH" || m === "DELETE";
}

// While the Settings page is open, every write to /api shows up in one
// "Saving… / Saved / Couldn't save" indicator. Watching fetch here means
// all of Settings' sections report their saves without each one having to
// be wired up individually, and it's removed again when the page closes.
export function startTrackingSaves() {
  if (originalFetch) return;
  originalFetch = window.fetch;
  const real = originalFetch.bind(window);
  const currentGeneration = ++generation;
  window.fetch = async (input, init) => {
    if (generation !== currentGeneration) return real(input, init);
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    const method =
      init?.method ?? (input instanceof Request ? input.method : "GET");
    const tracked = url.startsWith("/api/") && isWrite(method);
    if (!tracked) return real(input, init);
    clearConfirmation();
    if (pending === 0) batchFailed = false;
    pending += 1;
    saveState.value = "saving";
    try {
      const response = await real(input, init);
      finishWrite(!response.ok, currentGeneration);
      return response;
    } catch (err) {
      finishWrite(true, currentGeneration);
      throw err;
    }
  };
}

export function stopTrackingSaves() {
  if (!originalFetch) return;
  window.fetch = originalFetch;
  originalFetch = null;
  generation += 1;
  clearConfirmation();
  pending = 0;
  batchFailed = false;
  saveState.value = "idle";
  savedAt.value = null;
}
