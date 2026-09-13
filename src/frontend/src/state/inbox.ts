import { ref } from "vue";
import { listInbox } from "../services/media";

// shared across the sidebar badge and the Inbox page itself, the sidebar
// stays mounted across navigation, so it needs a way to learn about changes
// made on the Inbox page without re-fetching on every render
export const inboxCount = ref(0);

export async function refreshInboxCount() {
  try {
    inboxCount.value = (await listInbox()).length;
  } catch {
    // badge just doesn't update this tick, not worth surfacing an error
    // for a sidebar count
  }
}
