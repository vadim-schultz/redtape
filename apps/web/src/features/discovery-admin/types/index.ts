/** Paginated discovery task queue from the admin API. */

export type DiscoveryTaskListResponse = {
  items: unknown[];
  total: number;
  offset: number;
  limit: number;
};
