// Extra per-collection details the backend has no place for (a collection is
// just a tag on games): the description, whether it's pinned, and where it
// sits in "My order". Keyed by collection name in localStorage, the same tier
// as the manual-collections list and cover picks, so Collections can offer
// what Media's lists have without a backend row.
import { ref } from "vue";

export interface CollectionMeta {
  description?: string;
  pinned?: boolean;
  position?: number;
}

const META_KEY = "collectionMeta";
const MANUAL_KEY = "manualCollections";
const COVER_KEY = "collectionCoverPicks";
const ORDER_KEY = "collectionGameOrder";

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}
function writeJson(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // best-effort, the change just won't survive a reload
  }
}

export const collectionMeta = ref<Record<string, CollectionMeta>>(
  readJson(META_KEY, {}),
);

export function metaFor(name: string): CollectionMeta {
  return collectionMeta.value[name] ?? {};
}

export function updateMeta(name: string, patch: Partial<CollectionMeta>) {
  const next: CollectionMeta = { ...metaFor(name), ...patch };
  if (!next.description) delete next.description;
  if (!next.pinned) delete next.pinned;
  if (next.position === undefined) delete next.position;
  const all = { ...collectionMeta.value };
  if (Object.keys(next).length) all[name] = next;
  else delete all[name];
  collectionMeta.value = all;
  writeJson(META_KEY, all);
}

// the whole "My order": each name's position is its index in `names`
export function setCollectionOrder(names: string[]) {
  const all = { ...collectionMeta.value };
  names.forEach((name, position) => {
    all[name] = { ...(all[name] ?? {}), position };
  });
  collectionMeta.value = all;
  writeJson(META_KEY, all);
}

function moveKey(key: string, from: string, to: string) {
  const store = readJson<Record<string, unknown>>(key, {});
  if (!(from in store)) return;
  store[to] = store[from];
  delete store[from];
  writeJson(key, store);
}

// everything stored locally under a collection's name follows a rename
export function renameCollectionKeys(from: string, to: string) {
  if (from === to) return;
  moveKey(META_KEY, from, to);
  collectionMeta.value = readJson(META_KEY, {});
  moveKey(COVER_KEY, from, to);
  moveKey(ORDER_KEY, from, to);
  const manual = readJson<string[]>(MANUAL_KEY, []);
  if (manual.includes(from)) {
    writeJson(
      MANUAL_KEY,
      manual.map((n) => (n === from ? to : n)),
    );
  }
}

// and goes away with a delete
export function forgetCollectionKeys(name: string) {
  for (const key of [META_KEY, COVER_KEY, ORDER_KEY]) {
    const store = readJson<Record<string, unknown>>(key, {});
    if (name in store) {
      delete store[name];
      writeJson(key, store);
    }
  }
  collectionMeta.value = readJson(META_KEY, {});
  const manual = readJson<string[]>(MANUAL_KEY, []);
  if (manual.includes(name)) {
    writeJson(
      MANUAL_KEY,
      manual.filter((n) => n !== name),
    );
  }
}
