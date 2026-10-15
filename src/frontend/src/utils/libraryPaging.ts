// Reading a library a page at a time, and keeping what is already loaded when it is
// read again, so coming back to a library never shrinks it to its first page and
// then refills it.

import type { MediaPage } from "../services/mediaApi";
import type { LibraryFilters } from "./libraryFilters";

export type PagedFilters = LibraryFilters & { statusBucket: string };
export const PAGE_SIZE = 100;
// a library that was loaded this recently is not read again when you come back
export const STALE_AFTER_MS = 2 * 60 * 1000;

type FetchPage<T> = (
  offset: number,
  limit: number,
  filters: PagedFilters,
) => Promise<MediaPage<T>>;

// The first page, then as many more as it takes to have `count` titles (or all of
// them). The first page carries the status counts and the ranks.
export async function fetchLoadedExtent<T>(
  fetchPage: FetchPage<T>,
  filters: PagedFilters,
  count: number,
): Promise<MediaPage<T>> {
  const first = await fetchPage(0, PAGE_SIZE, filters);
  const items = [...first.items];
  const wanted = Math.min(count, first.total);
  while (items.length < wanted) {
    const next = await fetchPage(items.length, PAGE_SIZE, filters);
    if (!next.items.length) break;
    items.push(...next.items);
  }
  return { ...first, items };
}
