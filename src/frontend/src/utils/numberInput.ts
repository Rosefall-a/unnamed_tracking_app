// A number box bound with v-model.number gives "" once it is emptied, not null.
// A server field that expects a number or nothing rejects "", so a cleared box
// has to become null before it is sent.
export function numberOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}
