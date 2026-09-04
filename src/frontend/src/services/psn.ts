export interface PsnStatus {
  connected: boolean
  validated_at: number | null
}

let mockStatus: PsnStatus = { connected: false, validated_at: null }

export async function fetchPsnStatus(): Promise<PsnStatus> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return { ...mockStatus }
  }

  const response = await fetch('/api/auth/me/psn/status', { credentials: 'include' })
  if (!response.ok) {
    throw new Error(`Failed to fetch PlayStation status: ${response.status} ${response.statusText}`)
  }
  return await response.json()
}

export async function connectPsn(npssoToken: string): Promise<PsnStatus> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    mockStatus = { connected: true, validated_at: Math.floor(Date.now() / 1000) }
    return { ...mockStatus }
  }

  const response = await fetch('/api/auth/me/psn', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ npsso_token: npssoToken }),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Failed to connect PlayStation account: ${response.status} ${response.statusText}`)
  }
  const result = await response.json()
  return { connected: true, validated_at: result.validated_at }
}

export async function disconnectPsn(): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    mockStatus = { connected: false, validated_at: null }
    return
  }

  const response = await fetch('/api/auth/me/psn', { method: 'DELETE', credentials: 'include' })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to disconnect PlayStation account: ${response.status} ${response.statusText} ${message}`)
  }
}
