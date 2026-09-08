// Named sub-scopes within one game (e.g. separate OSRS accounts), lets
// checklist items and screenshots be filtered down to one account instead
// of mixing every account's stuff together.

export interface GameProfile {
  id: string
  game_id: string
  name: string
  note: string | null
  stats: Record<string, string>
  wiseoldman_username: string | null
  created_at: number
}

export interface ProfileUpdate {
  name?: string
  note?: string | null
  stats?: Record<string, string>
  wiseoldman_username?: string | null
}

export interface TrashedGameProfile extends GameProfile {
  deleted_at: number
  purge_at: number
}

export async function listGameProfiles(gameId: string): Promise<GameProfile[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') return []
  const response = await fetch(`/api/game/${gameId}/profiles`, { credentials: 'include' })
  if (!response.ok) throw new Error(`Failed to list profiles: ${response.status} ${response.statusText}`)
  const body = await response.json()
  return body.profiles
}

export async function createGameProfile(gameId: string, name: string): Promise<GameProfile> {
  const response = await fetch(`/api/game/${gameId}/profiles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ name }),
  })
  if (!response.ok) throw new Error(`Failed to create profile: ${response.status} ${response.statusText}`)
  return await response.json()
}

export async function renameGameProfile(gameId: string, profileId: string, name: string): Promise<GameProfile> {
  return updateGameProfile(gameId, profileId, { name })
}

export async function updateGameProfile(gameId: string, profileId: string, payload: ProfileUpdate): Promise<GameProfile> {
  const response = await fetch(`/api/game/${gameId}/profiles/${profileId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  })
  if (!response.ok) throw new Error(`Failed to update profile: ${response.status} ${response.statusText}`)
  return await response.json()
}

export async function syncProfileWiseOldMan(gameId: string, profileId: string, username?: string): Promise<GameProfile> {
  const response = await fetch(`/api/game/${gameId}/profiles/${profileId}/sync-wiseoldman`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ username: username || null }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to sync WiseOldMan: ${response.status} ${response.statusText} ${message}`)
  }
  return await response.json()
}

// a dated copy of a profile's stats, written automatically on every sync
// or manual edit, so progression can be shown over time
export interface StatSnapshot {
  id: string
  recorded_at: number
  stats: Record<string, string>
  // raw integers (WiseOldMan syncs only, empty on a manually-edited
  // snapshot) used to compute an accurate day-to-day gain instead of
  // diffing level numbers, which can each span tens of thousands of XP
  xp: Record<string, number>
  kc: Record<string, number>
}

export async function fetchProfileStatHistory(gameId: string, profileId: string): Promise<StatSnapshot[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') return []
  const response = await fetch(`/api/game/${gameId}/profiles/${profileId}/stat-history`, { credentials: 'include' })
  if (!response.ok) throw new Error(`Failed to fetch stat history: ${response.status} ${response.statusText}`)
  const body = await response.json()
  return body.snapshots
}

// soft-delete, restorable for 7 days, same as every other trash-backed delete
export async function deleteGameProfile(gameId: string, profileId: string): Promise<void> {
  const response = await fetch(`/api/game/${gameId}/profiles/${profileId}`, {
    method: 'DELETE',
    credentials: 'include',
  })
  if (!response.ok) throw new Error(`Failed to delete profile: ${response.status} ${response.statusText}`)
}

export async function fetchGameProfileTrash(gameId: string): Promise<TrashedGameProfile[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') return []
  const response = await fetch(`/api/game/${gameId}/profiles/trash`, { credentials: 'include' })
  if (!response.ok) throw new Error(`Failed to fetch profile trash: ${response.status} ${response.statusText}`)
  const body = await response.json()
  return body.profiles
}

export async function restoreGameProfile(gameId: string, profileId: string): Promise<GameProfile> {
  const response = await fetch(`/api/game/${gameId}/profiles/${profileId}/restore`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!response.ok) throw new Error(`Failed to restore profile: ${response.status} ${response.statusText}`)
  return await response.json()
}

// --- Checklist ---------------------------------------------------------

export interface ChecklistItem {
  id: string
  game_id: string
  profile_id: string | null
  text: string
  done: boolean
  is_header: boolean
  sort_order: number
  created_at: number
}

// profileId omitted -> only game-level (unscoped) items; pass a profile id
// to get just that account's items instead of digging through every account
export async function listChecklist(gameId: string, profileId?: string | null): Promise<ChecklistItem[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') return []
  const params = new URLSearchParams()
  if (profileId) params.set('profile_id', profileId)
  else params.set('unscoped_only', 'true')
  const response = await fetch(`/api/game/${gameId}/checklist?${params.toString()}`, { credentials: 'include' })
  if (!response.ok) throw new Error(`Failed to list checklist: ${response.status} ${response.statusText}`)
  const body = await response.json()
  return body.items
}

export async function createChecklistItem(
  gameId: string,
  text: string,
  profileId?: string | null,
  isHeader = false,
): Promise<ChecklistItem> {
  const response = await fetch(`/api/game/${gameId}/checklist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ text, profile_id: profileId ?? null, is_header: isHeader }),
  })
  if (!response.ok) throw new Error(`Failed to create checklist item: ${response.status} ${response.statusText}`)
  return await response.json()
}

// sends the full new order for one scope (profile_id) in one call, used
// by both an up/down-arrow swap and (later) drag-and-drop, so there's only
// one "here's the new order" API instead of a different one per gesture
export async function reorderChecklist(gameId: string, profileId: string | null, itemIds: string[]): Promise<void> {
  const response = await fetch(`/api/game/${gameId}/checklist/reorder`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ profile_id: profileId, item_ids: itemIds }),
  })
  if (!response.ok) throw new Error(`Failed to reorder checklist: ${response.status} ${response.statusText}`)
}

export async function updateChecklistItem(
  gameId: string,
  itemId: string,
  payload: { text?: string; done?: boolean; is_header?: boolean; sort_order?: number },
): Promise<ChecklistItem> {
  const response = await fetch(`/api/game/${gameId}/checklist/${itemId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  })
  if (!response.ok) throw new Error(`Failed to update checklist item: ${response.status} ${response.statusText}`)
  return await response.json()
}

export async function deleteChecklistItem(gameId: string, itemId: string): Promise<void> {
  const response = await fetch(`/api/game/${gameId}/checklist/${itemId}`, {
    method: 'DELETE',
    credentials: 'include',
  })
  if (!response.ok) throw new Error(`Failed to delete checklist item: ${response.status} ${response.statusText}`)
}
