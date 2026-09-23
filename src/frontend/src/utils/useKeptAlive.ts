// For the pages App.vue keeps alive when you navigate away (the three
// libraries, Calendar, Lists). Their state and DOM survive, so swapping
// tabs shows the page exactly as you left it instead of remounting and
// flashing empty ("0 titles") while the data loads again. Two things
// still need doing by hand: pull fresh data in the background each time
// the page comes back, and put the scroll position back (the browser
// resets it when the route changes).
import { onActivated, onBeforeUnmount, onMounted } from "vue";

export function useKeptAlive(refresh: () => void): void {
  let firstActivation = true;
  let savedY = 0;
  let path = "";

  // Only record scroll while this page's own URL is showing: the reset to
  // the top that happens right after navigating away also fires a scroll
  // event, and it must not overwrite the position worth restoring.
  function onScroll() {
    if (window.location.pathname === path) savedY = window.scrollY;
  }

  onMounted(() => {
    path = window.location.pathname;
    window.addEventListener("scroll", onScroll, { passive: true });
  });
  onBeforeUnmount(() => window.removeEventListener("scroll", onScroll));

  onActivated(() => {
    path = window.location.pathname;
    if (firstActivation) {
      // the first activation is just the initial mount, which already loads
      firstActivation = false;
      return;
    }
    refresh();
    requestAnimationFrame(() => window.scrollTo(0, savedY));
  });
}
