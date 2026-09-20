// A keep-what-we-last-saw cache for library entities (movies, TV shows,
// anime). Every response that carries an entity is remembered here, so
// opening a title's page can draw it immediately from what the library
// list (or its last visit) already fetched, then quietly refresh it,
// instead of blanking to a loading state on every open.
export interface EntityCache<T extends { id: string }> {
  put(item: T): T;
  peek(id: string): T | undefined;
  remove(id: string): void;
  all(): T[];
  /** true once a full list has been loaded, so all() is complete */
  listLoaded(): boolean;
  markListLoaded(): void;
}

export function createEntityCache<T extends { id: string }>(): EntityCache<T> {
  const map = new Map<string, T>();
  let loaded = false;
  return {
    put(item) {
      map.set(item.id, item);
      return item;
    },
    peek: (id) => map.get(id),
    remove: (id) => void map.delete(id),
    all: () => [...map.values()],
    listLoaded: () => loaded,
    markListLoaded: () => {
      loaded = true;
    },
  };
}
