import { ref } from "vue";
import { fetchThemes, type ThemeCatalogue } from "../services/themes";

export const themeCatalogue = ref<ThemeCatalogue>({
  default_theme: "native",
  themes: [],
});
export const themesError = ref<string | null>(null);
export const themesLoaded = ref(false);
let generation = 0;
export async function refreshThemes(): Promise<void> {
  const current = ++generation;
  try {
    const result = await fetchThemes();
    if (current !== generation) return;
    themeCatalogue.value = result;
    themesError.value = null;
  } catch (error) {
    if (current !== generation) return;
    themesError.value =
      error instanceof Error
        ? error.message
        : "Could not load installed themes.";
  } finally {
    if (current === generation) themesLoaded.value = true;
  }
}
