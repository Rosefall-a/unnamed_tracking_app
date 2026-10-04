import { ref } from "vue";
import { fetchBranding, type Branding } from "../services/branding";

export const branding = ref<Branding>({
  app_name: "Archive",
  logo_url: null,
  favicon_url: "/api/branding/default-icon.svg",
});
export const brandingError = ref<string | null>(null);
export const brandingLoaded = ref(false);
let generation = 0;

export function applyBranding(value: Branding): void {
  generation++;
  branding.value = value;
  const favicon = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
  if (favicon) {
    favicon.href = value.favicon_url;
    favicon.type = value.favicon_url.endsWith(".svg")
      ? "image/svg+xml"
      : "image/png";
  }
}

export async function loadBranding(): Promise<void> {
  const requestGeneration = ++generation;
  brandingError.value = null;
  try {
    const result = await fetchBranding();
    if (requestGeneration !== generation) return;
    applyBranding(result);
    brandingLoaded.value = true;
  } catch (reason) {
    if (requestGeneration !== generation) return;
    brandingError.value =
      reason instanceof Error ? reason.message : "Could not load app branding.";
  }
}
