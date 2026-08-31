import type { Game, GameStatus } from '../types/game'

// The exact shape FastAPI sends — snake_case, matching the Python model
// field-for-field. This is deliberately a separate type from `Game`:
// nothing outside this file should ever see raw backend data directly.
interface BackendGame {
  id: string
  title: string
  sort_title: string
  description: string | null
  release_date: string | null
  developer: string | null
  publisher: string | null
  status: string
  priority: string | null
  favorite: boolean
  notes: string | null
  resume_note: string | null
  playtime_seconds: number
  rating_story: number | string | null
  rating_gameplay: number | string | null
  rating_soundtrack: number | string | null
  rating_overall: number | string | null
  personal_rank: number | null
  created_at: string
  updated_at: string
}

// Pydantic can serialize a Decimal as either a JSON number or a string
// depending on config — handle both rather than assume one
function toNumberOrNull(value: number | string | null): number | null {
  return value === null ? null : Number(value)
}

// backend sends "ON_HOLD", "WISHLIST", etc. — frontend expects
// 'on hold', 'wishlist' (lowercase, spaces not underscores)
function normalizeStatus(raw: string): GameStatus {
  return raw.toLowerCase().replace(/_/g, ' ') as GameStatus
}

export function mapBackendGame(raw: BackendGame): Game {
  return {
    id: raw.id,
    title: raw.title,
    // placeholders — the backend has no artwork yet
    coverColor: '#2a2a2a',
    coverImageUrl: `https://picsum.photos/seed/${raw.id}/1600/500`,
    status: normalizeStatus(raw.status),
    ratingOverall: toNumberOrNull(raw.rating_overall),
    ratingStory: toNumberOrNull(raw.rating_story),
    ratingGameplay: toNumberOrNull(raw.rating_gameplay),
    ratingSound: toNumberOrNull(raw.rating_soundtrack),
    // the backend has no achievements table yet
    achievementPercent: 0,
    achievements: [],
    description: raw.description,
    developer: raw.developer,
    publisher: raw.publisher,
    // no series field on the backend yet
    series: null,
    dateAdded: raw.created_at,
    // no tags/features tables yet
    tags: [],
    features: [],
    // the backend only tracks one flat playtime total, not per-platform —
    // synthesize a single "PC" entry until real multi-platform support exists
    platforms: [
      {
        platform: 'PC',
        playtimeMinutes: Math.round(raw.playtime_seconds / 60),
        completionPercent: null,
        lastPlayedAt: null,
      },
    ],
  }
}

export async function fetchGames(): Promise<Game[]> {
  const response = await fetch('/api/game/list')
  if (!response.ok) {
    throw new Error(`Failed to fetch games: ${response.status} ${response.statusText}`)
  }
  const raw: BackendGame[] = await response.json()
  return raw.map(mapBackendGame)
}

export async function fetchGame(id: string): Promise<Game | null> {
  const response = await fetch(`/api/game/get/${id}`)
  if (response.status === 404) return null
  if (!response.ok) {
    throw new Error(`Failed to fetch game ${id}: ${response.status} ${response.statusText}`)
  }
  const raw: BackendGame = await response.json()
  return mapBackendGame(raw)
}

export interface GameNoteListResponse {
  notes: string[]
}

export interface GameNoteWritePayload {
  content: string
}

export interface GameNoteActionResponse {
  game_id: string
  note_name: string
  path?: string
  status: 'saved' | 'deleted'
}

export async function listGameNotes(gameId: string): Promise<string[]> {
  const response = await fetch(`/api/game/${gameId}/notes`)
  if (!response.ok) {
    throw new Error(`Failed to list notes for game ${gameId}: ${response.status} ${response.statusText}`)
  }

  const data: GameNoteListResponse = await response.json()
  return data.notes ?? []
}

export async function fetchGameNote(gameId: string, noteName: string): Promise<string> {
  const response = await fetch(`/api/game/${gameId}/notes/${noteName}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch note ${noteName}: ${response.status} ${response.statusText}`)
  }

  return await response.text()
}

export async function saveGameNote(
  gameId: string,
  noteName: string,
  content: string,
): Promise<GameNoteActionResponse> {
  const response = await fetch(`/api/game/${gameId}/notes/${noteName}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content }),
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to save note ${noteName}: ${response.status} ${response.statusText} ${message}`)
  }

  return await response.json()
}

export async function deleteGameNote(gameId: string, noteName: string): Promise<GameNoteActionResponse> {
  const response = await fetch(`/api/game/${gameId}/notes/${noteName}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to delete note ${noteName}: ${response.status} ${response.statusText} ${message}`)
  }

  return await response.json()
}

export interface GameAssetUploadResponse {
  game_id: string
  asset_kind: string
  path: string
  status: string
}

export async function uploadGameAsset(
  gameId: string,
  assetKind: 'key_art' | 'banner' | 'logo' | 'icon',
  file: File,
): Promise<GameAssetUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`/api/game/${gameId}/assets/${assetKind}`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to upload ${assetKind}: ${response.status} ${response.statusText} ${message}`)
  }

  return await response.json()
}