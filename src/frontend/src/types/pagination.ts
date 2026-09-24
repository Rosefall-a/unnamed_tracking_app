export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  status_counts: Record<string, number>;
}
