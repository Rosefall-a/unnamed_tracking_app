export type ScanProvider =
  | 'Steam'
  | 'SteamGridDB'
  | 'IGDB'
  | 'RetroAchievements'
  | 'GiantBomb'
  | 'ScreenScraper'
  | 'HowLongToBeat'

export interface ScanSettings {
  id: string
  user_id: string
  provider_order: ScanProvider[]
  save_developer: boolean
  save_publisher: boolean
  save_series: boolean
  save_tags: boolean
  save_features: boolean
  save_description: boolean
  save_age_rating: boolean
  save_release_date: boolean
  save_time_to_beat: boolean
  created_at: number
  updated_at: number
}

export type ScanSettingsUpdate = Partial<
  Pick<
    ScanSettings,
    | 'provider_order'
    | 'save_developer'
    | 'save_publisher'
    | 'save_series'
    | 'save_tags'
    | 'save_features'
    | 'save_description'
    | 'save_age_rating'
    | 'save_release_date'
    | 'save_time_to_beat'
  >
>

const MOCK_SCAN_SETTINGS: ScanSettings = {
  id: 'mock',
  user_id: 'mock',
  provider_order: ['Steam', 'IGDB', 'GiantBomb', 'RetroAchievements', 'SteamGridDB', 'ScreenScraper', 'HowLongToBeat'],
  save_developer: true,
  save_publisher: true,
  save_series: true,
  save_tags: true,
  save_features: true,
  save_description: true,
  save_age_rating: true,
  save_release_date: true,
  save_time_to_beat: true,
  created_at: 0,
  updated_at: 0,
}

export async function fetchScanSettings(): Promise<ScanSettings> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return { ...MOCK_SCAN_SETTINGS }
  }

  const response = await fetch('/api/settings/scan', { credentials: 'include' })
  if (!response.ok) {
    throw new Error(`Failed to fetch scan settings: ${response.status} ${response.statusText}`)
  }
  return await response.json()
}

export async function updateScanSettings(payload: ScanSettingsUpdate): Promise<ScanSettings> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    Object.assign(MOCK_SCAN_SETTINGS, payload)
    return { ...MOCK_SCAN_SETTINGS }
  }

  const response = await fetch('/api/settings/scan', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to update scan settings: ${response.status} ${response.statusText} ${message}`)
  }
  return await response.json()
}

export async function fetchUploadLimits(): Promise<{ max_upload_size_mb: number }> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return { max_upload_size_mb: 15 }
  }

  const response = await fetch('/api/settings/upload-limits', { credentials: 'include' })
  if (!response.ok) {
    throw new Error(`Failed to fetch upload limits: ${response.status} ${response.statusText}`)
  }
  return await response.json()
}

export interface ProviderCredentialStatus {
  status: 'not_configured' | 'configured' | 'connected' | 'saved' | 'error'
  detail?: string | null
  app_configured?: boolean
}

const MOCK_PROVIDER_CREDENTIALS: Record<string, ProviderCredentialStatus> = {}

export async function fetchProviderCredentials(): Promise<Record<string, ProviderCredentialStatus>> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return { ...MOCK_PROVIDER_CREDENTIALS }
  }

  const response = await fetch('/api/settings/provider-credentials', { credentials: 'include' })
  if (!response.ok) {
    throw new Error(`Failed to fetch provider credentials: ${response.status} ${response.statusText}`)
  }
  return await response.json()
}

export async function saveProviderCredentials(
  provider: string,
  fields: Record<string, string>,
): Promise<ProviderCredentialStatus> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    const result: ProviderCredentialStatus = { status: 'connected' }
    MOCK_PROVIDER_CREDENTIALS[provider] = { status: 'configured' }
    return result
  }

  const response = await fetch(`/api/settings/provider-credentials/${encodeURIComponent(provider)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ fields }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to save ${provider} credentials: ${response.status} ${response.statusText} ${message}`)
  }
  return await response.json()
}

export async function deleteProviderCredentials(provider: string): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    delete MOCK_PROVIDER_CREDENTIALS[provider]
    return
  }

  const response = await fetch(`/api/settings/provider-credentials/${encodeURIComponent(provider)}`, {
    method: 'DELETE',
    credentials: 'include',
  })
  if (!response.ok) {
    throw new Error(`Failed to disconnect ${provider}: ${response.status} ${response.statusText}`)
  }
}
