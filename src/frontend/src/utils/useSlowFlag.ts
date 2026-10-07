// True only once `waiting` has stayed true for `delay` ms. A loading skeleton
// that appears for a fraction of a second before the content looks like a
// flicker, so show it only when the wait is long enough to need it.
import { onBeforeUnmount, ref, watch, type Ref } from "vue";

export function useSlowFlag(waiting: Ref<boolean>, delay = 300) {
  const slow = ref(false);
  let timer: ReturnType<typeof setTimeout> | null = null;
  const clear = () => {
    if (timer !== null) clearTimeout(timer);
    timer = null;
  };
  watch(
    waiting,
    (now) => {
      clear();
      slow.value = false;
      if (now) timer = setTimeout(() => (slow.value = true), delay);
    },
    { immediate: true },
  );
  onBeforeUnmount(clear);
  return slow;
}
