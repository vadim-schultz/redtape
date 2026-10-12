import { useMemo, useState } from "react";

import type { DiscoverySource, DiscoveryTaskStatus } from "../types";

export type DiscoveryTaskFilters = {
  status: DiscoveryTaskStatus;
  source: DiscoverySource | null;
  setStatus: (status: DiscoveryTaskStatus) => void;
  setSource: (source: DiscoverySource | null) => void;
};

/** Local filter state for the crawler queue; default ``pending`` tasks. */
export function useDiscoveryTaskFilters(): DiscoveryTaskFilters {
  const [status, setStatus] = useState<DiscoveryTaskStatus>("pending");
  const [source, setSource] = useState<DiscoverySource | null>(null);

  return useMemo(
    () => ({ status, source, setStatus, setSource }),
    [status, source],
  );
}
