export type MediaKind = 'screenshot' | 'clip'

export interface MediaItem {
  filename: string
  kind: MediaKind
  url: string
}

export interface UploadResult {
  filename: string
  status: 'saved' | 'rejected'
  kind?: MediaKind
  reason?: string
}

async function uploadFiles(url: string, files: File[]): Promise<UploadResult[]> {
  const form = new FormData()
  for (const file of files) form.append('files', file)
  const response = await fetch(url, { method: 'POST', credentials: 'include', body: form })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Upload failed: ${response.status} ${response.statusText} ${message}`)
  }
  const body = await response.json()
  return body.results
}

export async function uploadGameScreenshots(gameId: string, files: File[]): Promise<UploadResult[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return files.map((f) => ({ filename: f.name, status: 'saved', kind: f.type.startsWith('video/') ? 'clip' : 'screenshot' }))
  }
  return uploadFiles(`/api/game/${gameId}/screenshots`, files)
}

export async function listGameScreenshots(gameId: string): Promise<MediaItem[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') return []
  const response = await fetch(`/api/game/${gameId}/screenshots`, { credentials: 'include' })
  if (!response.ok) throw new Error(`Failed to list media: ${response.status} ${response.statusText}`)
  const body = await response.json()
  return body.media
}

export async function deleteGameScreenshot(gameId: string, kind: MediaKind, filename: string): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') return
  const response = await fetch(`/api/game/${gameId}/screenshots/${kind}/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
    credentials: 'include',
  })
  if (!response.ok) throw new Error(`Failed to delete media: ${response.status} ${response.statusText}`)
}

export async function uploadToInbox(files: File[]): Promise<UploadResult[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return files.map((f) => ({ filename: f.name, status: 'saved', kind: f.type.startsWith('video/') ? 'clip' : 'screenshot' }))
  }
  return uploadFiles('/api/media/inbox', files)
}

export async function listInbox(): Promise<MediaItem[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') return []
  const response = await fetch('/api/media/inbox', { credentials: 'include' })
  if (!response.ok) throw new Error(`Failed to list inbox: ${response.status} ${response.statusText}`)
  const body = await response.json()
  return body.media
}

export async function deleteInboxMedia(kind: MediaKind, filename: string): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') return
  const response = await fetch(`/api/media/inbox/${kind}/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
    credentials: 'include',
  })
  if (!response.ok) throw new Error(`Failed to delete media: ${response.status} ${response.statusText}`)
}

export async function assignInboxMedia(kind: MediaKind, filename: string, gameId: string): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') return
  const response = await fetch(`/api/media/inbox/${kind}/${encodeURIComponent(filename)}/assign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ game_id: gameId }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to assign media: ${response.status} ${response.statusText} ${message}`)
  }
}
