export interface AdminUser {
  id: string
  username: string
  email: string
  is_admin: boolean
  is_active?: boolean
  created_at?: number
}

export interface CreateUserPayload {
  username: string
  email: string
  password: string
  isAdmin: boolean
}

const MOCK_USERS: AdminUser[] = [
  { id: 'mock', username: 'MockUser', email: 'mock@example.com', is_admin: true },
]

export async function listUsers(): Promise<AdminUser[]> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    return [...MOCK_USERS]
  }

  const response = await fetch('/api/auth/users', { credentials: 'include' })
  if (!response.ok) {
    throw new Error(`Failed to list users: ${response.status} ${response.statusText}`)
  }
  return await response.json()
}

export async function createUser(payload: CreateUserPayload): Promise<AdminUser> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    const user: AdminUser = {
      id: crypto.randomUUID(),
      username: payload.username,
      email: payload.email,
      is_admin: payload.isAdmin,
    }
    MOCK_USERS.push(user)
    return user
  }

  const response = await fetch('/api/auth/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      username: payload.username,
      email: payload.email,
      password: payload.password,
      is_admin: payload.isAdmin,
    }),
  })
  if (response.status === 409) {
    throw new Error('That username or email is already taken.')
  }
  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to create user: ${response.status} ${response.statusText} ${message}`)
  }
  return await response.json()
}

export async function deleteUser(id: string): Promise<void> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    const index = MOCK_USERS.findIndex((u) => u.id === id)
    if (index !== -1) MOCK_USERS.splice(index, 1)
    return
  }

  const response = await fetch(`/api/auth/users/${id}`, { method: 'DELETE', credentials: 'include' })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to delete user: ${response.status} ${response.statusText} ${message}`)
  }
}

export async function setUserAdmin(id: string, isAdmin: boolean): Promise<AdminUser> {
  if (import.meta.env.VITE_USE_MOCK_DATA === 'true') {
    const user = MOCK_USERS.find((u) => u.id === id)
    if (user) user.is_admin = isAdmin
    return user ?? MOCK_USERS[0]
  }

  const response = await fetch(`/api/auth/users/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ is_admin: isAdmin }),
  })
  if (!response.ok) {
    const message = await response.text()
    throw new Error(`Failed to update user: ${response.status} ${response.statusText} ${message}`)
  }
  return await response.json()
}
