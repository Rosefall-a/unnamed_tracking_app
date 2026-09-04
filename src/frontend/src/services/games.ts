import { mockGames } from '../data/mockGames'
import type { AchievementsProvider, Game, GameStatus, GameLink, GameOwnership } from '../types/game'

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
  series: string | null
  tags: string[]
  features: string[]
  source: string | null
  age_rating: string | null
  time_to_beat_hours: number | string | null
  status: string
  priority: string | null
  favorite: boolean
  notes: string | null
  resume_note: string | null
  playtime_seconds: number
  purchase_date: number | null
  purchase_price: number | string | null
  purchase_price_currency_code: string | null
  physical_condition: string | null
  rating_story: number | string | null
  rating_gameplay: number | string | null
  rating_soundtrack: number | string | null
  rating_overall: number | string | null
  personal_rank: number | null
  // unix timestamps in seconds, not ISO strings
  created_at: number
  updated_at: number
  folder_location: string
}

// Pydantic can serialize a Decimal as either a JSON number or a string
// depending on config — handle both rather than assume one
function toNumberOrNull(value: number | string | null): number | null {
  return value === null ? null : Number(value)
}

function unixSecondsToIso(seconds: number | null): string | null {
  return seconds === null ? null : new Date(seconds * 1000).toISOString()
}

function unixSecondsToDateInput(seconds: number | null): string | null {
  return seconds === null ? null : new Date(seconds * 1000).toISOString().slice(0, 10)
}

function dateInputToUnixSeconds(dateStr: string | null): number | null {
  if (!dateStr) return null
  return Math.floor(new Date(dateStr).getTime() / 1000)
}

// backend sends "ON_HOLD", "WISHLIST", etc. — frontend expects
// 'on hold', 'wishlist' (lowercase, spaces not underscores)
function normalizeStatus(raw: string): GameStatus {
  return raw.toLowerCase().replace(/_/g, ' ') as GameStatus
}
// inverse of normalizeStatus — 'on hold' -> 'ON_HOLD'
function denormalizeStatus(status: GameStatus): string {
  return status.toUpperCase().replace(/ /g, '_')
}

export function mapBackendGame(raw: BackendGame): Game {
  return {
    id: raw.id,
    title: raw.title,
    // placeholders — the backend has no artwork yet
    coverColor: '#2a2a2a',
    coverImageUrl: `/api/game/${raw.id}/assets/key_art`,
    bannerImageUrl: `/api/game/${raw.id}/assets/banner`,
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
    series: raw.series,
    dateAdded: unixSecondsToIso(raw.created_at),
    folderLocation: raw.folder_location,
    releaseDate: raw.release_date,
    source: raw.source,
    ageRating: raw.age_rating,
    timeToBeatHours: toNumberOrNull(raw.time_to_beat_hours),
    region: null,
    language: null,
    achievementsProvider: null,
    links: [],
    ownership: {
      // no backend column for digital-vs-physical — inferred from whether
      // a physical condition was recorded, otherwise left unset
      format: raw.physical_condition ? 'physical' : null,
      purchaseDate: unixSecondsToDateInput(raw.purchase_date),
      price: toNumberOrNull(raw.purchase_price),
      priceCurrency: raw.purchase_price_currency_code,
      condition: raw.physical_condition,
    },
    tags: raw.tags,
    features: raw.features,
    favorite: raw.favorite,
    collections: [],
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
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return mockGames
  }
  const response = await fetch('/api/game/list')
  if (!response.ok) {
    throw new Error(`Failed to fetch games: ${response.status} ${response.statusText}`)
  }
  const raw: BackendGame[] = await response.json()
  return raw.map(mapBackendGame)
}

export async function fetchGame(id: string): Promise<Game | null> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return mockGames.find((g) => g.id === id) ?? null
  }
  const response = await fetch(`/api/game/get/${id}`)
  if (response.status === 404) return null
  if (!response.ok) {
    throw new Error(`Failed to fetch game ${id}: ${response.status} ${response.statusText}`)
  }
  const raw: BackendGame = await response.json()
  return mapBackendGame(raw)
}

export interface MetadataSearchResult {
  provider: string
  provider_id: string
  title: string
  description: string | null
  release_date: string | null
  developer: string | null
  publisher: string | null
  age_rating: string | null
  time_to_beat_hours: number | string | null
  tags: string[]
  features: string[]
  links: GameLink[]
  key_art_url: string | null
  key_art_urls: string[]
  banner_url: string | null
  banner_urls: string[]
  logo_url: string | null
  logo_urls: string[]
  icon_url: string | null
  icon_urls: string[]
}

export interface MetadataSearchResponse {
  results: MetadataSearchResult[]
  steamgriddb_configured: boolean
  provider_errors: string[]
}

export async function searchGameMetadata(query: string): Promise<MetadataSearchResponse> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return { results: [], steamgriddb_configured: false, provider_errors: [] }
  }
  const response = await fetch(`/api/game/metadata/search?query=${encodeURIComponent(query)}`)
  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Metadata search failed: ${response.status} ${message}`)
  }
  return await response.json()
}

export type RefreshMetadataResult = 'updated' | 'no-match' | 'error'

export interface RefreshMetadataOutcome {
  status: RefreshMetadataResult
  keyArtAdded: boolean
  bannerAdded: boolean
}

export interface RefreshMetadataOptions {
  // re-fetch description/developer/publisher/release date/age rating/tags/features
  updateText: boolean
  // fetch cover + banner art for games that currently have none
  fillMissingArt: boolean
  // replace art even on games that already have some — off by default since
  // this is the one setting that can actually destroy something you set
  // deliberately (a manually-uploaded cover, art from an earlier refresh)
  overwriteExistingArt: boolean
}

export const DEFAULT_REFRESH_OPTIONS: RefreshMetadataOptions = {
  updateText: true,
  fillMissingArt: true,
  overwriteExistingArt: false,
}

async function gameAssetExists(gameId: string, assetKind: 'key_art' | 'banner'): Promise<boolean> {
  const response = await fetch(`/api/game/${gameId}/assets/${assetKind}`)
  return response.ok
}

// Re-pulls metadata for one game from Steam (+ SteamGridDB art data) and
// applies whichever pieces `options` asks for. Only applies anything when a
// result's title matches the game's current title exactly (case-insensitive)
// — a fuzzy/no match is reported back rather than guessing. Never touches
// notes (a wholly separate API this never calls). Image behavior is fully
// opt-in per `options`: by default a currently-blank slot can be filled in,
// but nothing already set is replaced unless overwriteExistingArt is on.
export async function refreshGameMetadata(
  game: Game,
  options: RefreshMetadataOptions = DEFAULT_REFRESH_OPTIONS,
): Promise<RefreshMetadataOutcome> {
  const outcome: RefreshMetadataOutcome = { status: 'error', keyArtAdded: false, bannerAdded: false }
  try {
    const { results } = await searchGameMetadata(game.title)
    const match = results.find((r) => r.title.trim().toLowerCase() === game.title.trim().toLowerCase())
    if (!match) {
      outcome.status = 'no-match'
      return outcome
    }

    if (options.updateText) {
      const input: NewGameInput = {
        title: game.title,
        sortTitle: null,
        folderLocation: game.folderLocation ?? '',
        status: game.status,
        description: match.description,
        developer: match.developer,
        publisher: match.publisher,
        series: game.series,
        releaseDate: match.release_date,
        dateAdded: game.dateAdded,
        source: match.provider,
        ageRating: match.age_rating,
        timeToBeatHours: toNumberOrNull(match.time_to_beat_hours) ?? game.timeToBeatHours,
        region: game.region,
        language: game.language,
        achievementsProvider: game.achievementsProvider,
        ratingOverall: game.ratingOverall,
        ratingStory: game.ratingStory,
        ratingGameplay: game.ratingGameplay,
        ratingSound: game.ratingSound,
        tags: match.tags,
        features: match.features,
        links: match.links,
        ownership: game.ownership,
        favorite: game.favorite,
        collections: game.collections,
      }
      await updateGame(game.id, input)
    }
    outcome.status = 'updated'

    if (import.meta.env.VITE_USE_MOCK_DATA !== 'true' && (options.fillMissingArt || options.overwriteExistingArt)) {
      if (match.key_art_url && (options.overwriteExistingArt || !(await gameAssetExists(game.id, 'key_art')))) {
        await attachGameAssetFromUrl(game.id, 'key_art', match.key_art_url)
        outcome.keyArtAdded = true
      }
      if (match.banner_url && (options.overwriteExistingArt || !(await gameAssetExists(game.id, 'banner')))) {
        await attachGameAssetFromUrl(game.id, 'banner', match.banner_url)
        outcome.bannerAdded = true
      }
    }

    return outcome
  } catch {
    outcome.status = 'error'
    return outcome
  }
}

export interface NewGameInput {
  title: string
  sortTitle: string | null
  folderLocation: string
  status: GameStatus
  description: string | null
  developer: string | null
  publisher: string | null
  series: string | null
  releaseDate: string | null
  dateAdded: string | null
  source: string | null
  ageRating: string | null
  timeToBeatHours: number | null
  region: string | null
  language: string | null
  achievementsProvider: AchievementsProvider
  ratingOverall: number | null
  ratingStory: number | null
  ratingGameplay: number | null
  ratingSound: number | null
  tags: string[]
  features: string[]
  links: GameLink[]
  ownership: GameOwnership
  favorite: boolean
  collections: string[]
}

export async function createGame(input: NewGameInput): Promise<Game> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    const newGame: Game = {
      id: crypto.randomUUID(),
      title: input.title,
      coverColor: '#2a2a2a',
      coverImageUrl: `https://picsum.photos/seed/${input.title}/1200/1800`,
      bannerImageUrl: `https://picsum.photos/seed/${input.title}-banner/1600/500`,
      status: input.status,
      ratingOverall: input.ratingOverall,
      ratingStory: input.ratingStory,
      ratingGameplay: input.ratingGameplay,
      ratingSound: input.ratingSound,
      achievementPercent: 0,
      achievements: [],
      description: input.description,
      developer: input.developer,
      publisher: input.publisher,
      series: input.series,
      dateAdded: input.dateAdded,
      tags: input.tags,
      features: input.features,
      folderLocation: input.folderLocation || null,
      releaseDate: input.releaseDate,
      source: input.source,
      ageRating: input.ageRating,
      timeToBeatHours: input.timeToBeatHours,
      region: input.region,
      language: input.language,
      achievementsProvider: input.achievementsProvider,
      links: input.links,
      ownership: input.ownership,
      platforms: [],
      favorite: input.favorite,
      collections: input.collections,
    }
    mockGames.push(newGame)
    return newGame
  }

  const response = await fetch('/api/game/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: input.title,
      sort_title: input.sortTitle,
      folder_location: input.folderLocation,
      status: denormalizeStatus(input.status),
      favorite: input.favorite,
      description: input.description,
      developer: input.developer,
      publisher: input.publisher,
      series: input.series,
      release_date: input.releaseDate,
      source: input.source,
      age_rating: input.ageRating,
      time_to_beat_hours: input.timeToBeatHours,
      rating_overall: input.ratingOverall,
      rating_story: input.ratingStory,
      rating_gameplay: input.ratingGameplay,
      rating_soundtrack: input.ratingSound,
      tags: input.tags,
      features: input.features,
      purchase_date: dateInputToUnixSeconds(input.ownership.purchaseDate),
      purchase_price: input.ownership.price,
      purchase_price_currency_code: input.ownership.priceCurrency,
      physical_condition: input.ownership.condition,
    }),
  })

  if (response.status === 409) {
    const body = await response.json()
    throw new Error(body.detail?.message ?? 'A game with that folder name already exists.')
  }

  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to create game: ${response.status} ${response.statusText} ${message}`)
  }

  const raw: BackendGame = await response.json()
  return mapBackendGame(raw)
}
function stripEmpty<T extends Record<string, unknown>>(obj: T): Partial<T> {
  const result: Partial<T> = {}
  for (const key in obj) {
    const value = obj[key]
    const isEmpty =
      value === null ||
      value === '' ||
      (Array.isArray(value) && value.length === 0)
    if (!isEmpty) result[key] = value
  }
  return result
}

export async function updateGame(id: string, input: NewGameInput): Promise<Game> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    const index = mockGames.findIndex((g) => g.id === id)
    if (index === -1) throw new Error(`Game ${id} not found`)
    const updated: Game = {
      ...mockGames[index],
      title: input.title,
      status: input.status,
      ratingOverall: input.ratingOverall,
      ratingStory: input.ratingStory,
      ratingGameplay: input.ratingGameplay,
      ratingSound: input.ratingSound,
      description: input.description,
      developer: input.developer,
      publisher: input.publisher,
      series: input.series,
      dateAdded: input.dateAdded,
      tags: input.tags,
      folderLocation: input.folderLocation || null,
      releaseDate: input.releaseDate,
      source: input.source,
      ageRating: input.ageRating,
      timeToBeatHours: input.timeToBeatHours,
      region: input.region,
      language: input.language,
      achievementsProvider: input.achievementsProvider,
      links: input.links,
      ownership: input.ownership,
      features: input.features,
    }
    mockGames[index] = updated
    return updated
  }

  const body = stripEmpty({
    title: input.title,
    sort_title: input.sortTitle,
    folder_location: input.folderLocation,
    status: denormalizeStatus(input.status),
    favorite: input.favorite,
    description: input.description,
    developer: input.developer,
    publisher: input.publisher,
    series: input.series,
    release_date: input.releaseDate,
    source: input.source,
    age_rating: input.ageRating,
    time_to_beat_hours: input.timeToBeatHours,
    rating_overall: input.ratingOverall,
    rating_story: input.ratingStory,
    rating_gameplay: input.ratingGameplay,
    rating_soundtrack: input.ratingSound,
    tags: input.tags,
    features: input.features,
    purchase_date: dateInputToUnixSeconds(input.ownership.purchaseDate),
    purchase_price: input.ownership.price,
    purchase_price_currency_code: input.ownership.priceCurrency,
    physical_condition: input.ownership.condition,
  })

  const response = await fetch(`/api/game/update/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (response.status === 409) {
    const errBody = await response.json()
    throw new Error(errBody.detail?.message ?? 'A game with that folder name already exists.')
  }

  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to update game ${id}: ${response.status} ${response.statusText} ${message}`)
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

// per-game note storage for mock mode — resets on page reload, same as mockGames itself
const mockNotesStore = new Map<string, Map<string, string>>()
function getMockNoteMap(gameId: string): Map<string, string> {
  if (!mockNotesStore.has(gameId)) mockNotesStore.set(gameId, new Map())
  return mockNotesStore.get(gameId)!
}

export async function listGameNotes(gameId: string): Promise<string[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return Array.from(getMockNoteMap(gameId).keys())
  }

  const response = await fetch(`/api/game/${gameId}/notes`)
  if (!response.ok) {
    throw new Error(`Failed to list notes for game ${gameId}: ${response.status} ${response.statusText}`)
  }

  const data: GameNoteListResponse = await response.json()
  return data.notes ?? []
}

export async function fetchGameNote(gameId: string, noteName: string): Promise<string> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return getMockNoteMap(gameId).get(noteName) ?? ''
  }

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
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    getMockNoteMap(gameId).set(noteName, content)
    return { game_id: gameId, note_name: noteName, status: 'saved' }
  }

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
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    getMockNoteMap(gameId).delete(noteName)
    return { game_id: gameId, note_name: noteName, status: 'deleted' }
  }

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

export async function attachGameAssetFromUrl(
  gameId: string,
  assetKind: 'key_art' | 'banner' | 'logo' | 'icon',
  url: string,
): Promise<GameAssetUploadResponse> {
  const response = await fetch(`/api/game/${gameId}/assets/${assetKind}/from-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to fetch ${assetKind} from URL: ${response.status} ${response.statusText} ${message}`)
  }

  return await response.json()
}

export async function setFavorite(gameId: string, favorite: boolean): Promise<Game> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    const index = mockGames.findIndex((g) => g.id === gameId)
    if (index === -1) throw new Error(`Game ${gameId} not found`)
    mockGames[index] = { ...mockGames[index], favorite }
    return mockGames[index]
  }

  const response = await fetch(`/api/game/update/${gameId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ favorite }),
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to update favorite: ${response.status} ${response.statusText} ${message}`)
  }

  const raw: BackendGame = await response.json()
  return mapBackendGame(raw)
}

export async function setStatus(gameId: string, status: GameStatus): Promise<Game> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    const index = mockGames.findIndex((g) => g.id === gameId)
    if (index === -1) throw new Error(`Game ${gameId} not found`)
    mockGames[index] = { ...mockGames[index], status }
    return mockGames[index]
  }

  const response = await fetch(`/api/game/update/${gameId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: denormalizeStatus(status) }),
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to update status: ${response.status} ${response.statusText} ${message}`)
  }

  const raw: BackendGame = await response.json()
  return mapBackendGame(raw)
}

export async function addGameToCollection(gameId: string, collectionName: string): Promise<Game> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    const index = mockGames.findIndex((g) => g.id === gameId)
    if (index === -1) throw new Error(`Game ${gameId} not found`)
    const existing = mockGames[index].collections
    const collections = existing.includes(collectionName) ? existing : [...existing, collectionName]
    mockGames[index] = { ...mockGames[index], collections }
    return mockGames[index]
  }

  // no backend column for collections yet — nothing to persist against
  throw new Error('Collections are not supported by the backend yet.')
}

export async function removeGameFromCollection(gameId: string, collectionName: string): Promise<Game> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    const index = mockGames.findIndex((g) => g.id === gameId)
    if (index === -1) throw new Error(`Game ${gameId} not found`)
    const collections = mockGames[index].collections.filter((c) => c !== collectionName)
    mockGames[index] = { ...mockGames[index], collections }
    return mockGames[index]
  }

  throw new Error('Collections are not supported by the backend yet.')
}

export async function deleteGame(gameId: string): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    const index = mockGames.findIndex((g) => g.id === gameId)
    if (index !== -1) mockGames.splice(index, 1)
    return
  }

  const response = await fetch(`/api/game/delete/${gameId}`, { method: 'DELETE' })
  if (!response.ok && response.status !== 204) {
    const message = await response.text()
    throw new Error(`Failed to delete game ${gameId}: ${response.status} ${response.statusText} ${message}`)
  }
}