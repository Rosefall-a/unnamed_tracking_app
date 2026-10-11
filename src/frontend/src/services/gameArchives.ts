import { createSpeedTracker } from "../utils/uploadSpeed";

// Named, versioned save archives, "Main World", "Pre-Nether-Update
// Backup", etc., replacing the old convention of a save being just one
// anonymous uploaded file. kind is 'save' or 'world_save'; docs/modpacks
// stay on the simpler flat file system in services/media.ts.
export type ArchiveKind = "save" | "world_save";

export interface ArchiveVersion {
  id: string;
  filename: string;
  size: number;
  uploaded_at: number;
  url: string;
}

export interface GameArchiveData {
  id: string;
  name: string;
  note?: string | null;
  tags?: string[];
  kind: ArchiveKind;
  created_at: number;
  updated_at: number;
  versions: ArchiveVersion[];
}

// real byte-level progress via XHR, same reasoning as uploadFiles in
// services/media.ts, fetch has no upload-progress event at all
function uploadWithProgress(
  url: string,
  method: "POST" | "PATCH",
  form: FormData | null,
  jsonBody: unknown | null,
  onProgress?: (fraction: number, speedLabel?: string) => void,
): Promise<GameArchiveData> {
  const trackSpeed = createSpeedTracker();
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url);
    xhr.withCredentials = true;
    if (form) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress)
          onProgress(e.loaded / e.total, trackSpeed(e.loaded, e.total));
      };
    } else {
      xhr.setRequestHeader("Content-Type", "application/json");
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(
            new Error(
              "Request succeeded but the response could not be parsed.",
            ),
          );
        }
      } else {
        reject(
          new Error(
            `Request failed: ${xhr.status} ${xhr.statusText} ${xhr.responseText}`,
          ),
        );
      }
    };
    xhr.onerror = () => reject(new Error("Request failed: network error."));
    xhr.send(form ?? JSON.stringify(jsonBody));
  });
}

// Mock mode keeps archives in memory for the session, like the media, so the
// Saves tab can be tried without a backend.
const mockArchives: GameArchiveData[] = [];
function mockVersion(file: File): ArchiveVersion {
  return {
    id: crypto.randomUUID(),
    filename: file.name,
    size: file.size,
    uploaded_at: Math.floor(Date.now() / 1000),
    url: URL.createObjectURL(file),
  };
}

export async function fetchArchives(
  gameId: string,
  kind: ArchiveKind,
): Promise<GameArchiveData[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true")
    // copies, like a real response, so a change shows up in the page
    return mockArchives
      .filter((a) => a.kind === kind)
      .map((a) => ({
        ...a,
        tags: [...(a.tags ?? [])],
        versions: [...a.versions],
      }));
  const response = await fetch(`/api/game/${gameId}/archives/${kind}`, {
    credentials: "include",
  });
  if (!response.ok)
    throw new Error(
      `Failed to fetch archives: ${response.status} ${response.statusText}`,
    );
  return await response.json();
}

export async function createArchive(
  gameId: string,
  kind: ArchiveKind,
  name: string,
  file: File,
  onProgress?: (fraction: number, speedLabel?: string) => void,
): Promise<GameArchiveData> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    const now = Math.floor(Date.now() / 1000);
    const created: GameArchiveData = {
      id: crypto.randomUUID(),
      name,
      kind,
      created_at: now,
      updated_at: now,
      versions: [mockVersion(file)],
    };
    mockArchives.push(created);
    return created;
  }
  const form = new FormData();
  form.append("name", name);
  form.append("file", file);
  return uploadWithProgress(
    `/api/game/${gameId}/archives/${kind}`,
    "POST",
    form,
    null,
    onProgress,
  );
}

export async function addArchiveVersion(
  gameId: string,
  archiveId: string,
  file: File,
  onProgress?: (fraction: number, speedLabel?: string) => void,
): Promise<GameArchiveData> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    const archive = mockArchives.find((a) => a.id === archiveId);
    if (!archive) throw new Error("Archive not found");
    archive.versions = [mockVersion(file), ...archive.versions];
    archive.updated_at = Math.floor(Date.now() / 1000);
    return { ...archive };
  }
  const form = new FormData();
  form.append("file", file);
  return uploadWithProgress(
    `/api/game/${gameId}/archives/${archiveId}/versions`,
    "POST",
    form,
    null,
    onProgress,
  );
}

// Changes whatever is given (name, note, tags) and leaves the rest alone.
export async function updateArchive(
  gameId: string,
  archiveId: string,
  patch: { name?: string; note?: string | null; tags?: string[] },
): Promise<GameArchiveData> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    const archive = mockArchives.find((a) => a.id === archiveId);
    if (!archive) throw new Error("Archive not found");
    if (patch.name !== undefined) archive.name = patch.name;
    if (patch.note !== undefined) archive.note = patch.note;
    if (patch.tags !== undefined) archive.tags = patch.tags;
    return { ...archive };
  }
  const response = await fetch(`/api/game/${gameId}/archives/${archiveId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(patch),
  });
  if (!response.ok)
    throw new Error(
      `Failed to save: ${response.status} ${response.statusText}`,
    );
  return await response.json();
}

export async function deleteArchive(
  gameId: string,
  archiveId: string,
): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") {
    const i = mockArchives.findIndex((a) => a.id === archiveId);
    if (i !== -1) mockArchives.splice(i, 1);
    return;
  }
  const response = await fetch(`/api/game/${gameId}/archives/${archiveId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok)
    throw new Error(
      `Failed to delete: ${response.status} ${response.statusText}`,
    );
}

// --- Trash (7-day soft-delete window before a delete becomes permanent) ---
export interface TrashedArchive extends GameArchiveData {
  deleted_at: number;
  purge_at: number;
}

export async function fetchArchiveTrash(
  gameId: string,
  kind: ArchiveKind,
): Promise<TrashedArchive[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === "true") return [];
  const response = await fetch(`/api/game/${gameId}/archives/${kind}/trash`, {
    credentials: "include",
  });
  if (!response.ok)
    throw new Error(
      `Failed to fetch trash: ${response.status} ${response.statusText}`,
    );
  return await response.json();
}

export async function restoreArchive(
  gameId: string,
  archiveId: string,
): Promise<GameArchiveData> {
  const response = await fetch(
    `/api/game/${gameId}/archives/${archiveId}/restore`,
    {
      method: "POST",
      credentials: "include",
    },
  );
  if (!response.ok)
    throw new Error(
      `Failed to restore: ${response.status} ${response.statusText}`,
    );
  return await response.json();
}

export async function restoreArchiveVersion(
  gameId: string,
  archiveId: string,
  versionId: string,
): Promise<GameArchiveData> {
  const response = await fetch(
    `/api/game/${gameId}/archives/${archiveId}/versions/${versionId}/restore`,
    {
      method: "POST",
      credentials: "include",
    },
  );
  if (!response.ok)
    throw new Error(
      `Failed to restore version: ${response.status} ${response.statusText}`,
    );
  return await response.json();
}

export async function deleteArchiveVersion(
  gameId: string,
  archiveId: string,
  versionId: string,
): Promise<GameArchiveData> {
  const response = await fetch(
    `/api/game/${gameId}/archives/${archiveId}/versions/${versionId}`,
    {
      method: "DELETE",
      credentials: "include",
    },
  );
  if (!response.ok)
    throw new Error(
      `Failed to delete version: ${response.status} ${response.statusText}`,
    );
  return await response.json();
}
