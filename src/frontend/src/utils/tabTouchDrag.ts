// Moving a tab on a touch screen, where the browser's drag and drop does not
// work. Hold a tab for a moment, then slide it along the bar. A quick swipe
// still scrolls the bar, because the hold is cancelled as soon as the finger
// moves before it is up.
import type { Ref } from "vue";

const HOLD_MS = 400;
const SLOP_PX = 8;
// how close to an edge of the bar the finger has to be to scroll it
const EDGE_PX = 36;

export function useTabTouchDrag(opts: {
  scroller: Ref<HTMLElement | null>;
  dragging: Ref<string | null>;
  dropMark: Ref<{ id: string; after: boolean } | null>;
  drop: (id: string) => void;
  end: () => void;
}) {
  let timer: ReturnType<typeof setTimeout> | null = null;
  let startX = 0;
  let startY = 0;

  function clearHold() {
    if (timer) clearTimeout(timer);
    timer = null;
  }

  function touchStart(e: TouchEvent, id: string) {
    if (e.touches.length !== 1) return;
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
    clearHold();
    timer = setTimeout(() => {
      timer = null;
      opts.dragging.value = id;
      navigator.vibrate?.(15);
    }, HOLD_MS);
  }

  function touchMove(e: TouchEvent) {
    const touch = e.touches[0];
    if (!opts.dragging.value) {
      const moved =
        Math.abs(touch.clientX - startX) > SLOP_PX ||
        Math.abs(touch.clientY - startY) > SLOP_PX;
      if (moved) clearHold();
      return;
    }
    // the finger is moving a tab now, not scrolling the page
    e.preventDefault();
    const bar = opts.scroller.value;
    if (bar) {
      const box = bar.getBoundingClientRect();
      if (touch.clientX < box.left + EDGE_PX) bar.scrollLeft -= 8;
      else if (touch.clientX > box.right - EDGE_PX) bar.scrollLeft += 8;
    }
    const under = document
      .elementFromPoint(touch.clientX, touch.clientY)
      ?.closest<HTMLElement>("[data-tab-id]");
    const id = under?.dataset.tabId;
    if (!under || !id || id === opts.dragging.value) {
      opts.dropMark.value = null;
      return;
    }
    const box = under.getBoundingClientRect();
    opts.dropMark.value = {
      id,
      after: touch.clientX > box.left + box.width / 2,
    };
  }

  function touchEnd(e: TouchEvent) {
    clearHold();
    if (!opts.dragging.value) return;
    // stops the tap that ends a move from also opening the tab
    e.preventDefault();
    const target = opts.dropMark.value?.id;
    if (target) opts.drop(target);
    else opts.end();
  }

  function touchCancel() {
    clearHold();
    if (opts.dragging.value) opts.end();
  }

  return { touchStart, touchMove, touchEnd, touchCancel };
}
