import { computed, ref, watch } from "vue";

interface SavedTitle {
  title: string;
  lockedFields?: string[];
}

export function useTitleProtection(
  saved: () => SavedTitle | null | undefined,
  title: () => string,
) {
  const titleLockOverride = ref<boolean | undefined>();
  watch(saved, () => {
    titleLockOverride.value = undefined;
  });
  const titleProtected = computed({
    get: () =>
      titleLockOverride.value ??
      ((saved()?.lockedFields ?? []).includes("title") ||
        (!!saved() && title().trim() !== saved()?.title)),
    set: (value: boolean) => {
      titleLockOverride.value = value;
    },
  });
  return { titleProtected, titleLockOverride };
}
