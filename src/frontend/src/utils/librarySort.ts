import { getUi } from "../state/uiState";

// The sort a media library is in, remembered per library (on the server). The server reads a page
// in this order, so the first page already holds the best of the whole library
// (a sort done only over what is loaded would show the best of that page).

export type LibrarySort =
  | "rank"
  | "score"
  | "title"
  | "title_desc"
  | "added"
  | "year_new"
  | "year_old"
  | "progress";

export const LIBRARY_SORTS: readonly LibrarySort[] = [
  "rank",
  "score",
  "title",
  "title_desc",
  "added",
  "year_new",
  "year_old",
  "progress",
];

export const DEFAULT_LIBRARY_SORT: LibrarySort = "rank";

export function readSavedSort(kind: "movie" | "tv" | "anime"): LibrarySort {
  const saved = getUi<LibrarySort>(`librarySort:${kind}`, DEFAULT_LIBRARY_SORT);
  return LIBRARY_SORTS.includes(saved) ? saved : DEFAULT_LIBRARY_SORT;
}
