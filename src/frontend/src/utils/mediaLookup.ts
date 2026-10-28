// What the media forms' "Look up metadata" panel hands around: one change per field
// a provider would fill in, with what is there now, what it would become, and
// whether it starts ticked. Adding a title ticks everything; editing ticks only
// the fields that are empty, so a value you wrote is never replaced by accident.

export interface LookupChange {
  key: string;
  label: string;
  from: string;
  to: string;
  // what the form applies for this field when it is ticked
  value: unknown;
  // pictures to show next to the change: the new one, and the one it replaces
  image?: string | null;
  fromImage?: string | null;
  checked: boolean;
}

export interface LookupApply {
  key: string;
  value: unknown;
}

// The `offer` helper a form's build function uses: it adds a change only when
// the provider has a value that differs from the current one.
export function makeOffer(
  adding: boolean,
  current: Record<string, string>,
  out: LookupChange[],
) {
  return (
    key: string,
    label: string,
    to: string | number | null | undefined,
    value: unknown = to,
  ) => {
    const next = (to ?? "").toString().trim();
    const from = current[key] ?? "";
    if (!next || next === from.trim()) return;
    out.push({
      key,
      label,
      from,
      to: next,
      value,
      checked: adding || !from.trim(),
    });
  };
}

export function listText(items: string[] | null | undefined): string {
  return (items ?? []).join(", ");
}
