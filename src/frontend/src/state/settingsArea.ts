import { ref } from "vue";

// The Settings page resolves core aliases and plugin destinations in one place.
// Sidebar highlighting follows that resolved area rather than guessing from IDs.
export const activeSettingsArea = ref<
  "preferences" | "account" | "administration"
>("preferences");
