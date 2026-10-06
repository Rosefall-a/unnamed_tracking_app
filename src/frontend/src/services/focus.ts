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
      'a[href], button, input, select, textarea, summary, [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((element) => {
    if (
      element.tabIndex < 0 ||
      element.matches(":disabled, [inert]") ||
      !element.getClientRects().length
    )
      return false;
    // A closed details element can leave descendant layout boxes present,
    // although only its summary participates in native keyboard navigation.
    for (
      let parent = element.parentElement;
      parent;
      parent = parent.parentElement
    ) {
      if (
        parent instanceof HTMLDetailsElement &&
        !parent.open &&
        !parent.querySelector(":scope > summary")?.contains(element)
      )
        return false;
    }
    return true;
  });
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
