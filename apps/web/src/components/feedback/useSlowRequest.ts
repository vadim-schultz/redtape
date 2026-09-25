import { useIsFetching } from "@tanstack/react-query";
import { useEffect, useState } from "react";

/** True once some query has been in flight continuously for `thresholdMs`. */
export function useSlowRequest(thresholdMs: number): boolean {
  const isFetching = useIsFetching() > 0;
  const [isSlow, setIsSlow] = useState(false);

  useEffect(() => {
    if (!isFetching) {
      setIsSlow(false);
      return;
    }
    const timer = setTimeout(() => setIsSlow(true), thresholdMs);
    return () => clearTimeout(timer);
  }, [isFetching, thresholdMs]);

  return isSlow;
}
