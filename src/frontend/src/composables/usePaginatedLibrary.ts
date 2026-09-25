import { ref } from "vue";

export interface LibraryPage<T> {
  items: T[];
  total: number;
}

interface Options<T> {
  pageSize: number;
  fetchPage: (offset: number, limit: number, search: string) => Promise<LibraryPage<T>>;
}

export function usePaginatedLibrary<T>({ pageSize, fetchPage }: Options<T>) {
  const items = ref<T[]>([]);
  const totalCount = ref(0);
  const loading = ref(true);
  const loadingMore = ref(false);
  const hasMore = ref(true);
  let requestToken = 0;
  let currentSearch = "";

  async function load(search = "") {
    const token = ++requestToken;
    currentSearch = search;
    loading.value = true;
    loadingMore.value = false;
    try {
      const page = await fetchPage(0, pageSize, search);
      if (token !== requestToken) return;
      items.value = page.items;
      totalCount.value = page.total;
      hasMore.value = items.value.length < totalCount.value;
    } finally {
      if (token === requestToken) loading.value = false;
    }
  }

  async function loadMore(search = currentSearch) {
    if (!hasMore.value || loadingMore.value) return;
    const token = requestToken;
    loadingMore.value = true;
    try {
      const page = await fetchPage(items.value.length, pageSize, search);
      if (token !== requestToken) return;
      items.value.push(...page.items);
      totalCount.value = page.total;
      hasMore.value = items.value.length < totalCount.value;
    } finally {
      if (token === requestToken) loadingMore.value = false;
    }
  }

  async function loadAll(search = currentSearch) {
    if (search !== currentSearch) await load(search);
    while (hasMore.value) {
      await loadMore();
    }
  }

  function invalidate() {
    requestToken++;
  }

  return {
    items,
    totalCount,
    loading,
    loadingMore,
    hasMore,
    load,
    loadMore,
    loadAll,
    invalidate,
  };
}
