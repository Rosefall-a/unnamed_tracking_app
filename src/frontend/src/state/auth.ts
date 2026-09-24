import { ref } from "vue";
import { fetchCurrentUser } from "../services/auth";
import type { CurrentUser } from "../services/auth";

export const currentUser = ref<CurrentUser | null>(null);
export const authChecked = ref(false);
export const startupError = ref(false);

export async function checkAuth() {
  try {
    currentUser.value = await fetchCurrentUser();
  } catch {
    currentUser.value = null;
    startupError.value = true;
  }
  authChecked.value = true;
}
