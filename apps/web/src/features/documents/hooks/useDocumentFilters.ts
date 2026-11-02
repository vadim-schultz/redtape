import { useSearchParams } from "react-router-dom";

import type { GroupedTerm } from "../../taxonomy/types";
import {
  FILTER_PARAMS,
  readCodes,
  readSelection,
  withToggledDomain,
  withSelection,
  withoutParams,
} from "../utils/filterParams";
import {
  toggleGroupSelection,
  toggleSituationSelection,
  type GroupSelection,
} from "../utils/groupSelection";

export interface DocumentFilters {
  domains: string[];
  groups: string[];
  situations: string[];
  toggleDomain: (code: string) => void;
  toggleGroup: (code: string) => void;
  toggleSituation: (code: string) => void;
  /** Drops the chips and returns to the first page; search and sort stay. */
  clear: () => void;
  /** Drops the chips and the search term and returns to the first page; sort stays. */
  clearAll: () => void;
}

type Toggle = (
  selection: GroupSelection,
  code: string,
  situations: GroupedTerm[],
) => GroupSelection;

/** URL search params are the single source of truth for list filters.
 *
 * `situations` is the loaded taxonomy; it tells which situations belong to a group so a
 * group and its situations are never selected together. */
export function useDocumentFilters(
  situations: GroupedTerm[] = [],
): DocumentFilters {
  const [params, setParams] = useSearchParams();

  const select = (toggle: Toggle) => (code: string) =>
    setParams((prev) =>
      withSelection(prev, toggle(readSelection(prev), code, situations)),
    );

  return {
    domains: readCodes(params, "domain"),
    groups: readCodes(params, "group"),
    situations: readCodes(params, "situation"),
    toggleDomain: (code) => setParams((prev) => withToggledDomain(prev, code)),
    toggleGroup: select(toggleGroupSelection),
    toggleSituation: select(toggleSituationSelection),
    clear: () => setParams((prev) => withoutParams(prev, [...FILTER_PARAMS])),
    clearAll: () =>
      setParams((prev) => withoutParams(prev, [...FILTER_PARAMS, "q"])),
  };
}
