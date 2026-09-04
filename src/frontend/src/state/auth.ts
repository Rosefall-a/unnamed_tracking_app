import { ref } from 'vue'
import { fetchCurrentUser } from '../services/auth'
import type { CurrentUser } from '../services/auth'

export const currentUser = ref<CurrentUser | null>(null)
export const authChecked = ref(false)

export async function checkAuth() {
    currentUser.value = await fetchCurrentUser()
    authChecked.value = true
}
