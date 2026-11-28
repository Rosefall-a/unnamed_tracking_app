// A library's tab row is one line that scrolls sideways when its tabs do not
// fit (a phone, or many tabs you made). This tracks whether there is more to
// either side, for the fades, and keeps the open tab in view.
import { nextTick, onUnmounted, ref, watch, type WatchSource } from "vue";

export function useTabScroll(openTab: WatchSource<unknown>) {
  const scroller = ref<HTMLElement | null>(null);
  const moreLeft = ref(false);
  const moreRight = ref(false);

  function measure() {
    const el = scroller.value;
    if (!el) return;
    moreLeft.value = el.scrollLeft > 2;
    moreRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 2;
  }
  function showOpenTab() {
    scroller.value
      ?.querySelector<HTMLElement>(".active")
      ?.scrollIntoView({ block: "nearest", inline: "nearest" });
    measure();
  }

  let resize: ResizeObserver | null = null;
  watch(scroller, (el) => {
    resize?.disconnect();
    if (!el) return;
    resize = new ResizeObserver(measure);
    resize.observe(el);
    void nextTick(showOpenTab);
  });
  watch(openTab, () => void nextTick(showOpenTab));
  onUnmounted(() => resize?.disconnect());

  return { scroller, moreLeft, moreRight, measure };
}
