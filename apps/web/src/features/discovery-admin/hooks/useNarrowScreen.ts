import { useSyncExternalStore } from "react";

/** Narrower than Chakra's `md` breakpoint (48em), where the flow switches from the graph to the list. */
const NARROW_QUERY = "(max-width: 47.98em)";

/** Notify when the query's answer changes, so the view follows a resize or a rotation. */
function subscribe(onChange: () => void): () => void {
  const query = window.matchMedia(NARROW_QUERY);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

function isNarrow(): boolean {
  return window.matchMedia(NARROW_QUERY).matches;
}

/** Whether the viewport is below the `md` breakpoint. Server rendering assumes a wide screen. */
export function useNarrowScreen(): boolean {
  return useSyncExternalStore(subscribe, isNarrow, () => false);
}
