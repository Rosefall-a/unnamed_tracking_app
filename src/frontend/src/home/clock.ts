// One shared clock for everything on Home that counts down. It ticks every
// second, but only while something is using it.
import { onBeforeUnmount, onMounted, ref } from "vue";

const now = ref(Date.now());
let users = 0;
let timer: number | undefined;

export function useNow() {
  onMounted(() => {
    users += 1;
    now.value = Date.now();
    if (users === 1)
      timer = window.setInterval(() => (now.value = Date.now()), 1000);
  });
  onBeforeUnmount(() => {
    users -= 1;
    if (users === 0 && timer !== undefined) {
      window.clearInterval(timer);
      timer = undefined;
    }
  });
  return now;
}

// "In 3h 12m", or "Airing now" once it has started: the line shown on a card
export const airPhrase = (text: string) =>
  text === "Now" ? "Airing now" : `In ${text}`;

// "2d 4h", "3h 12m", "12m 05s": the two biggest units that still matter
export function countdown(
  seconds: number,
  now: number,
  precise: boolean,
): string {
  const left = Math.floor(seconds - now / 1000);
  if (left <= 0) return "Now";
  const d = Math.floor(left / 86_400);
  const h = Math.floor((left % 86_400) / 3600);
  const m = Math.floor((left % 3600) / 60);
  const s = left % 60;
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0)
    return precise
      ? `${h}h ${String(m).padStart(2, "0")}m ${String(s).padStart(2, "0")}s`
      : `${h}h ${m}m`;
  return precise || m < 5 ? `${m}m ${String(s).padStart(2, "0")}s` : `${m}m`;
}
