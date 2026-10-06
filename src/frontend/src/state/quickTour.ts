import { ref } from "vue";

export const quickTourActive = ref(false);
export const quickTourRun = ref(0);
export const shortcutsHelpOpen = ref(false);

export function startQuickTour() {
  quickTourRun.value++;
  quickTourActive.value = true;
}

export function stopQuickTour() {
  quickTourActive.value = false;
}
