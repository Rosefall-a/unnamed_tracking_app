import { createSpeedTracker } from '../utils/uploadSpeed'

// Named, versioned save archives — "Main World", "Pre-Nether-Update
// Backup", etc. — replacing the old convention of a save being just one
// anonymous uploaded file. kind is 'save' or 'world_save'; docs/modpacks
// stay on the simpler flat file system in services/media.ts.
export type ArchiveKind = 'save' | 'world_save'

export interface ArchiveVersion {
  id: string
  filename: string
  size: number
  uploaded_at: number
  url: string
}

export interface GameArchiveData {
  id: string
  name: string
  kind: ArchiveKind
  created_at: number
  updated_at: number
  versions: ArchiveVersion[]
}

// real byte-level progress via XHR, same reasoning as uploadFiles in
// services/media.ts — fetch has no upload-progress event at all
function uploadWithProgress(
  url: string,
  method: 'POST' | 'PATCH',
  form: FormData | null,
  jsonBody: unknown | null,
  onProgress?: (fraction: number, speedLabel?: string) => void,
): Promise<GameArchiveData> {
  const trackSpeed = createSpeedTracker()
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open(method, url)
    xhr.withCredentials = true
    if (form) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total, trackSpeed(e.loaded, e.total))
      }
    } else {
      xhr.setRequestHeader('Content-Type', 'application/json')
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText))
        } catch {
          reject(new Error('Request succeeded but the response could not be parsed.'))
        }
      } else {
        reject(new Error(`Request failed: ${xhr.status} ${xhr.statusText} ${xhr.responseText}`))
      }
    }
    xhr.onerror = () => reject(new Error('Request failed: network error.'))
    xhr.send(form ?? JSON.stringify(jsonBody))
  })
}

export async function fetchArchives(gameId: string, kind: ArchiveKind): Promise<GameArchiveData[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') return []
  const response = await fetch(`/api/game/${gameId}/archives/${kind}`, { credentials: 'include' })
  if (!response.ok) throw new Error(`Failed to fetch archives: ${response.status} ${response.statusText}`)
  return await response.json()
}

export async function createArchive(
  gameId: string,
  kind: ArchiveKind,
  name: string,
  file: File,
  onProgress?: (fraction: number, speedLabel?: string) => void,
): Promise<GameArchiveData> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return { id: crypto.randomUUID(), name, kind, created_at: 0, updated_at: 0, versions: [] }
  }
  const form = new FormData()
  form.append('name', name)
  form.append('file', file)
  return uploadWithProgress(`/api/game/${gameId}/archives/${kind}`, 'POST', form, null, onProgress)
}

export async function addArchiveVersion(
  gameId: string,
  archiveId: string,
  file: File,
  onProgress?: (fraction: number, speedLabel?: string) => void,
): Promise<GameArchiveData> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return { id: archiveId, name: '', kind: 'save', created_at: 0, updated_at: 0, versions: [] }
  }
  const form = new FormData()
  form.append('file', file)
  return uploadWithProgress(`/api/game/${gameId}/archives/${archiveId}/versions`, 'POST', form, null, onProgress)
}

export async function renameArchive(gameId: string, archiveId: string, name: string): Promise<GameArchiveData> {
  const response = await fetch(`/api/game/${gameId}/archives/${archiveId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ name }),
  })
  if (!response.ok) throw new Error(`Failed to rename: ${response.status} ${response.statusText}`)
  return await response.json()
}

export async function deleteArchive(gameId: string, archiveId: string): Promise<void> {
  const response = await fetch(`/api/game/${gameId}/archives/${archiveId}`, {
    method: 'DELETE',
    credentials: 'include',
  })
  if (!response.ok) throw new Error(`Failed to delete: ${response.status} ${response.statusText}`)
}

// --- Trash (7-day soft-delete window before a delete becomes permanent) ---
export interface TrashedArchive extends GameArchiveData {
  deleted_at: number
  purge_at: number
}

export async function fetchArchiveTrash(gameId: string, kind: ArchiveKind): Promise<TrashedArchive[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') return []
  const response = await fetch(`/api/game/${gameId}/archives/${kind}/trash`, { credentials: 'include' })
  if (!response.ok) throw new Error(`Failed to fetch trash: ${response.status} ${response.statusText}`)
  return await response.json()
}

export async function restoreArchive(gameId: string, archiveId: string): Promise<GameArchiveData> {
  const response = await fetch(`/api/game/${gameId}/archives/${archiveId}/restore`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!response.ok) throw new Error(`Failed to restore: ${response.status} ${response.statusText}`)
  return await response.json()
}

export async function restoreArchiveVersion(gameId: string, archiveId: string, versionId: string): Promise<GameArchiveData> {
  const response = await fetch(`/api/game/${gameId}/archives/${archiveId}/versions/${versionId}/restore`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!response.ok) throw new Error(`Failed to restore version: ${response.status} ${response.statusText}`)
  return await response.json()
}

export async function deleteArchiveVersion(gameId: string, archiveId: string, versionId: string): Promise<GameArchiveData> {
  const response = await fetch(`/api/game/${gameId}/archives/${archiveId}/versions/${versionId}`, {
    method: 'DELETE',
    credentials: 'include',
  })
  if (!response.ok) throw new Error(`Failed to delete version: ${response.status} ${response.statusText}`)
  return await response.json()
}

// --- World Map (BlueMap render of a world_save archive's latest version) ---
export type WorldMapStatus = 'idle' | 'rendering' | 'done' | 'error'

export interface WorldMapEntry extends GameArchiveData {
  status: WorldMapStatus
  detail: string | null
  updated_at_status: number | null
  has_thumbnail: boolean
}

export async function fetchWorldMaps(gameId: string): Promise<WorldMapEntry[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') return []
  const response = await fetch(`/api/game/${gameId}/world-map/worlds`, { credentials: 'include' })
  if (!response.ok) throw new Error(`Failed to fetch worlds: ${response.status} ${response.statusText}`)
  return await response.json()
}

export async function renderWorldMap(gameId: string, archiveId: string): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') return
  const response = await fetch(`/api/game/${gameId}/world-map/${archiveId}/render`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to start map render: ${response.status} ${response.statusText} ${message}`)
  }
}

export function worldMapViewUrl(gameId: string, archiveId: string): string {
  return `/api/game/${gameId}/world-map/${archiveId}/view/`
}

export function worldMapThumbnailUrl(gameId: string, archiveId: string): string {
  return `/api/game/${gameId}/world-map/${archiveId}/thumbnail`
}
