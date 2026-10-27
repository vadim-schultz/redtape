import { useMemo, useState } from "react";

import type {
  DiscoverySource,
  DiscoveryTaskKind,
  DiscoveryTaskStatus,
} from "../types";

export type DiscoveryTaskFilters = {
  status: DiscoveryTaskStatus;
  source: DiscoverySource | null;
  kind: DiscoveryTaskKind | null;
  setStatus: (status: DiscoveryTaskStatus) => void;
  setSource: (source: DiscoverySource | null) => void;
  setKind: (kind: DiscoveryTaskKind | null) => void;
};

/** Local filter state for the crawler queue; default ``pending`` tasks of every kind. */
export function useDiscoveryTaskFilters(): DiscoveryTaskFilters {
  const [status, setStatus] = useState<DiscoveryTaskStatus>("pending");
  const [source, setSource] = useState<DiscoverySource | null>(null);
  const [kind, setKind] = useState<DiscoveryTaskKind | null>(null);

  return useMemo(
    () => ({ status, source, kind, setStatus, setSource, setKind }),
    [status, source, kind],
  );
}
