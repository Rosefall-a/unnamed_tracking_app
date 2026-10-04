import { ref } from "vue";
import { fetchCurrentUser } from "../services/auth";
import type { CurrentUser } from "../services/auth";

export const currentUser = ref<CurrentUser | null>(null);
export const authChecked = ref(false);
export const authCheckFailed = ref(false);
let checkGeneration = 0;

export async function ensureAuthChecked() {
  if (!authChecked.value || authCheckFailed.value) await checkAuth();
}

export async function checkAuth() {
  const generation = ++checkGeneration;
  authCheckFailed.value = false;
  try {
    const user = await fetchCurrentUser();
    if (generation !== checkGeneration) return;
    currentUser.value = user;
  } catch {
    if (generation !== checkGeneration) return;
    authCheckFailed.value = true;
    // Keep auth failure separate from a confirmed unauthenticated response
    // so startup routing can distinguish an unavailable backend from login.
    currentUser.value = null;
  }
  authChecked.value = true;
}
