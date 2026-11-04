/** One free-tier resource in its current period. */
export type DiscoveryBudget = {
  resource: string;
  period: string;
  cap: number;
  used: number;
  remaining: number;
  exhausted: boolean;
};

export type DiscoveryBudgetsResponse = {
  items: DiscoveryBudget[];
  stored_bytes: number;
  stored_bytes_cap: number;
};
