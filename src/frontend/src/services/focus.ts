// Keep Tab cycling inside modal content, including the end of the sequence
// where some browsers otherwise focus their chrome. Native dialog still owns
// background inertness and focus restoration.
export function containModalTab(
  event: KeyboardEvent,
  root: HTMLElement | null,
): void {
  if (event.key !== "Tab" || !root) return;
  const controls = Array.from(
    root.querySelectorAll<HTMLElement>(
      'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])',
    ),
  ).filter(
    (element) =>
      !element.matches(":disabled, [inert]") &&
      element.getClientRects().length > 0,
  );
  const first = controls[0];
  const last = controls.at(-1);
  if (!first || !last) {
    event.preventDefault();
    root.focus();
    return;
  }
  if (
    (event.shiftKey && document.activeElement === first) ||
    (!event.shiftKey && document.activeElement === last)
  ) {
    event.preventDefault();
    (event.shiftKey ? last : first).focus();
  }
}
