// A background image that is only fetched once its element is about to scroll
// into view. Used for picture tiles that are CSS backgrounds (so they cannot
// use <img loading="lazy">): v-lazy-bg="url".
import type { Directive } from "vue";

const observer =
  typeof IntersectionObserver === "undefined"
    ? null
    : new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (!entry.isIntersecting) continue;
            const el = entry.target as HTMLElement;
            observer?.unobserve(el);
            if (el.dataset.lazyBg)
              el.style.backgroundImage = `url(${el.dataset.lazyBg})`;
          }
        },
        // start a little before it is on screen, so it is there when it is
        { rootMargin: "300px" },
      );

function apply(el: HTMLElement, url: string | null | undefined) {
  observer?.unobserve(el);
  if (!url) {
    delete el.dataset.lazyBg;
    el.style.backgroundImage = "";
    return;
  }
  if (!observer) {
    el.style.backgroundImage = `url(${url})`;
    return;
  }
  el.dataset.lazyBg = url;
  el.style.backgroundImage = "";
  observer.observe(el);
}

export const vLazyBg: Directive<HTMLElement, string | null | undefined> = {
  mounted: (el, binding) => apply(el, binding.value),
  updated: (el, binding) => {
    if (binding.value !== binding.oldValue) apply(el, binding.value);
  },
  unmounted: (el) => observer?.unobserve(el),
};
