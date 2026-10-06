// "action, drama, sci-fi" from a comma-separated text box
export function splitList(input: string): string[] {
  return input
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}
