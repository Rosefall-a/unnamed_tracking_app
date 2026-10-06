// For the pages App.vue keeps alive when you navigate away (the three
// libraries, Calendar, Lists). Their state and DOM survive, so swapping
// tabs preserves the page's loaded data instead of remounting and
// flashing empty ("0 titles") while the data loads again. Two things
// still need doing by hand: pull fresh data in the background each time
// the page comes back. The router owns scrolling: fresh visits start at the
// top and browser Back/Forward can restore their history position.
import { onActivated } from "vue";

export function useKeptAlive(refresh: () => void): void {
  let firstActivation = true;
  onActivated(() => {
    if (firstActivation) {
      // the first activation is just the initial mount, which already loads
      firstActivation = false;
      return;
    }
    refresh();
  });
}
