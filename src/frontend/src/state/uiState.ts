// What someone chose or made on a page, kept where it belongs:
// - real data (collections and their details, smart collection rules,
//   achievement pins and notes, note drafts, filter presets, the Home Pick
//   again, the "seen it" flags) is saved on the server (/api/ui-state), so it is
//   in the database, in backups, and on every device;
// - how this device shows things (sidebar, view modes, sorts, filters, tabs,
//   card sizes) stays in this browser, like the caches elsewhere in the app.
// Pages use the same getUi/setUi for both; the name decides which.
import { ref, shallowRef } from "vue";

const SERVER_NAMES = new Set([
  "manualCollections",
  "collectionMeta",
  "collectionCoverPicks",
  "collectionGameOrder",
  "smartCollections",
  "gameLibraryFilterPresets",
  "seenWelcomeTour",
  "seenBulkEditHint",
]);
const SERVER_PREFIXES = ["achievementLocal:", "noteDraft:", "homePick:"];
// kept only while the tab is open
const TAB_PREFIXES = ["libraryStatus:"];

export function savedOnServer(key: string): boolean {
  return (
    SERVER_NAMES.has(key) || SERVER_PREFIXES.some((p) => key.startsWith(p))
  );
}
function tabOnly(key: string): boolean {
  return TAB_PREFIXES.some((p) => key.startsWith(p));
}

const MOCK = import.meta.env.VITE_USE_MOCK_DATA === "true";
const NAME = /^[A-Za-z0-9:_.-]{1,200}$/;

// ---- this browser ----

function storeFor(key: string): Storage | null {
  try {
    return tabOnly(key) ? sessionStorage : localStorage;
  } catch {
    return null;
  }
}

// A plain word ("pinned", "true", "260") is kept as written, which is how the
// app always stored these; anything else as JSON.
function encode(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value);
}
function decode(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function readLocal(key: string): { found: boolean; value: unknown } {
  const raw = storeFor(key)?.getItem(key) ?? null;
  return raw === null
    ? { found: false, value: undefined }
    : { found: true, value: decode(raw) };
}

// read through a version number so pages update when a value changes
const localVersion = ref(0);

// ---- the server ----

const serverValues = shallowRef<Record<string, unknown>>({});
const loadedFor = ref<string | null>(null);
// a failed save, so a page can say its choice did not stick
export const uiSaveError = ref<string | null>(null);

async function send(
  method: "PUT" | "DELETE",
  key: string,
  value?: unknown,
): Promise<boolean> {
  if (MOCK) return true;
  try {
    const response = await fetch(`/api/ui-state/${encodeURIComponent(key)}`, {
      method,
      credentials: "include",
      headers:
        method === "PUT" ? { "Content-Type": "application/json" } : undefined,
      body: method === "PUT" ? JSON.stringify({ value }) : undefined,
    });
    if (!response.ok) throw new Error(`${response.status}`);
    uiSaveError.value = null;
    return true;
  } catch {
    uiSaveError.value = "A change could not be saved to the server.";
    return false;
  }
}

// Real data an older version kept in this browser goes to the server once. Each
// browser copy is deleted only after the server says it has it.
async function moveRealDataToServer(): Promise<void> {
  const found: Record<string, unknown> = {};
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const name = localStorage.key(i);
      const raw = name ? localStorage.getItem(name) : null;
      if (!name || raw === null || !NAME.test(name) || !savedOnServer(name))
        continue;
      found[name] = decode(raw);
    }
  } catch {
    return;
  }
  if (!Object.keys(found).length) return;
  const response = await fetch("/api/ui-state/import", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ values: found }),
  });
  if (!response.ok) return;
  const { stored } = (await response.json()) as { stored: string[] };
  for (const name of stored) localStorage.removeItem(name);
}

// A version of this change sent everything in the browser to the server,
// including what belongs to this device (and to other sites that once ran at
// this address). That is written back here, and removed from the server only
// once it is safely in the browser again.
async function bringBackDeviceValues(
  saved: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const keep: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(saved)) {
    if (savedOnServer(key)) {
      keep[key] = value;
      continue;
    }
    try {
      if (localStorage.getItem(key) === null) {
        // other sites' settings (BlueMap) were JSON, words included
        const raw = key.startsWith("bluemap-")
          ? JSON.stringify(value)
          : encode(value);
        localStorage.setItem(key, raw);
      }
      if (localStorage.getItem(key) === null) throw new Error("not stored");
    } catch {
      keep[key] = value;
      continue;
    }
    await send("DELETE", key);
  }
  return keep;
}

/** Loads this person's saved data; again only when someone else signs in. */
export async function loadUiState(userId: string): Promise<void> {
  if (MOCK || loadedFor.value === userId) return;
  try {
    await moveRealDataToServer();
  } catch {
    // the browser copies stay where they were and are tried again next time
  }
  try {
    const response = await fetch("/api/ui-state", { credentials: "include" });
    const saved = response.ok
      ? ((await response.json()) as Record<string, unknown>)
      : {};
    serverValues.value = await bringBackDeviceValues(saved);
    localVersion.value++;
  } catch {
    serverValues.value = {};
  }
  loadedFor.value = userId;
}

/** Forgets the loaded server data, on sign-out. */
export function clearUiState(): void {
  serverValues.value = {};
  loadedFor.value = null;
}

// ---- what pages use ----

export function getUi<T>(key: string, fallback: T): T {
  if (savedOnServer(key))
    return key in serverValues.value
      ? (serverValues.value[key] as T)
      : fallback;
  void localVersion.value;
  const { found, value } = readLocal(key);
  return found ? (value as T) : fallback;
}

export function hasUi(key: string): boolean {
  if (savedOnServer(key)) return key in serverValues.value;
  void localVersion.value;
  return readLocal(key).found;
}

const pending = new Map<string, ReturnType<typeof setTimeout>>();

/** Saves a choice. Quick repeats of real data (typing a draft) send only the
 * last one to the server. */
export function setUi(key: string, value: unknown): void {
  if (!savedOnServer(key)) {
    try {
      storeFor(key)?.setItem(key, encode(value));
    } catch {
      // without storage the choice holds until the page is reloaded
    }
    localVersion.value++;
    return;
  }
  serverValues.value = { ...serverValues.value, [key]: value };
  clearTimeout(pending.get(key));
  pending.set(
    key,
    setTimeout(() => {
      pending.delete(key);
      void send("PUT", key, value);
    }, 300),
  );
}

export function removeUi(key: string): void {
  if (!savedOnServer(key)) {
    try {
      storeFor(key)?.removeItem(key);
    } catch {
      // nothing to remove
    }
    localVersion.value++;
    return;
  }
  if (!(key in serverValues.value)) return;
  const { [key]: _gone, ...rest } = serverValues.value;
  void _gone;
  serverValues.value = rest;
  clearTimeout(pending.get(key));
  pending.delete(key);
  void send("DELETE", key);
}
