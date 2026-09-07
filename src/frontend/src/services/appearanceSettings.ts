export type BadgeStyle = 'none' | 'glow' | 'border' | 'ribbon' | 'corner_badge'
export type BadgePlacement = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'

export interface AppearanceSettings {
  id: string
  user_id: string
  completion_badge_style: BadgeStyle
  completion_badge_color: string
  completion_badge_placement: BadgePlacement
  completion_badge_image_url: string | null
  created_at: number
  updated_at: number
}

export type AppearanceSettingsUpdate = Partial<
  Pick<AppearanceSettings, 'completion_badge_style' | 'completion_badge_color' | 'completion_badge_placement'>
>

const MOCK_APPEARANCE: AppearanceSettings = {
  id: 'mock',
  user_id: 'mock',
  completion_badge_style: 'border',
  completion_badge_color: '#d4af37',
  completion_badge_placement: 'top-right',
  completion_badge_image_url: null,
  created_at: 0,
  updated_at: 0,
}

export async function fetchAppearanceSettings(): Promise<AppearanceSettings> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return { ...MOCK_APPEARANCE }
  }
  const response = await fetch('/api/settings/appearance', { credentials: 'include' })
  if (!response.ok) {
    throw new Error(`Failed to fetch appearance settings: ${response.status} ${response.statusText}`)
  }
  return await response.json()
}

export async function updateAppearanceSettings(payload: AppearanceSettingsUpdate): Promise<AppearanceSettings> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    Object.assign(MOCK_APPEARANCE, payload)
    return { ...MOCK_APPEARANCE }
  }
  const response = await fetch('/api/settings/appearance', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to update appearance settings: ${response.status} ${response.statusText} ${message}`)
  }
  return await response.json()
}

export async function uploadBadgeImage(file: File): Promise<AppearanceSettings> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    MOCK_APPEARANCE.completion_badge_image_url = URL.createObjectURL(file)
    return { ...MOCK_APPEARANCE }
  }
  const form = new FormData()
  form.append('file', file)
  const response = await fetch('/api/settings/appearance/badge-image', {
    method: 'POST',
    credentials: 'include',
    body: form,
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to upload badge image: ${response.status} ${response.statusText} ${message}`)
  }
  return await response.json()
}

export async function deleteBadgeImage(): Promise<AppearanceSettings> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    MOCK_APPEARANCE.completion_badge_image_url = null
    return { ...MOCK_APPEARANCE }
  }
  const response = await fetch('/api/settings/appearance/badge-image', {
    method: 'DELETE',
    credentials: 'include',
  })
  if (!response.ok) {
    throw new Error(`Failed to delete badge image: ${response.status} ${response.statusText}`)
  }
  return await response.json()
}
