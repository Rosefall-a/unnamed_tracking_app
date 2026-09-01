import type { Game, Achievement } from '../types/game'
import { MOCK_GAMES } from '../data/mockGames'

const USE_MOCK_DATA = process.env.VITE_USE_MOCK_DATA === 'true' // Set to false when backend API is ready

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options)

  const contentType = response.headers.get('content-type') || ''
  
  // If the server returned HTML (e.g. 404 fallback page), catch it cleanly
  if (contentType.includes('text/html')) {
    throw new Error(`API endpoint returned HTML instead of JSON (${response.status} ${response.statusText}). Check backend routing.`)
  }

  if (!response.ok) {
    throw new Error(`HTTP Error ${response.status}: ${response.statusText}`)
  }

  return response.json() as Promise<T>
}

export async function fetchGame(id: string): Promise<Game> {
  if (USE_MOCK_DATA) {
    const game = MOCK_GAMES.find((g) => g.id === id)
    if (!game) throw new Error('Game not found')
    return game
  }
  return fetchJSON<Game>(`/api/games/${id}`)
}

export async function listGameNotes(gameId: string): Promise<string[]> {
  if (USE_MOCK_DATA) {
    return ['install-notes', 'boss-strategies', 'mods-list']
  }
  return fetchJSON<string[]>(`/api/games/${gameId}/notes`)
}

export async function fetchGameNote(gameId: string, noteName: string): Promise<string> {
  if (USE_MOCK_DATA) {
    return `# Notes for ${noteName}\n- Sample note content for testing.`
  }
  const data = await fetchJSON<{ content: string }>(`/api/games/${gameId}/notes/${noteName}`)
  return data.content
}

export async function saveGameNote(gameId: string, noteName: string, content: string): Promise<void> {
  if (USE_MOCK_DATA) return
  await fetchJSON(`/api/games/${gameId}/notes/${noteName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
}

export async function deleteGameNote(gameId: string, noteName: string): Promise<void> {
  if (USE_MOCK_DATA) return
  await fetchJSON(`/api/games/${gameId}/notes/${noteName}`, {
    method: 'DELETE',
  })
}