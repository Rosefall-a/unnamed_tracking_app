// The rest of a paginated list in one parallel burst instead of one page after
// another, so a big library costs about one round trip, not one per page.
export async function fetchRemaining<T>(
  fetchPage: (offset: number, limit: number) => Promise<{ items: T[] }>,
  have: number,
  total: number,
  size = 200,
): Promise<T[]> {
  const offsets: number[] = [];
  for (let o = have; o < total; o += size) offsets.push(o);
  const pages = await Promise.all(offsets.map((o) => fetchPage(o, size)));
  return pages.flatMap((p) => p.items);
}
