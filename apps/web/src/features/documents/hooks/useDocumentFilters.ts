import { useSearchParams } from "react-router-dom";

import type { GroupedTerm } from "../../taxonomy/types";
import {
  toggled,
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

const FILTER_PARAMS = ["domain", "group", "situation"] as const;

export type FilterAxis = (typeof FILTER_PARAMS)[number];

type Toggle = (
  selection: GroupSelection,
  code: string,
  situations: GroupedTerm[],
) => GroupSelection;

function readCodes(params: URLSearchParams, axis: FilterAxis): string[] {
  return [...new Set(params.getAll(axis).filter(Boolean))];
}

function readSelection(params: URLSearchParams): GroupSelection {
  return {
    groups: readCodes(params, "group"),
    situations: readCodes(params, "situation"),
  };
}

/** A copy of `params` without `names`; any change of the filters also leaves the current page. */
function withoutParams(
  params: URLSearchParams,
  names: string[],
): URLSearchParams {
  const next = new URLSearchParams(params);
  [...names, "offset"].forEach((name) => next.delete(name));
  return next;
}

function withCodes(
  params: URLSearchParams,
  axis: FilterAxis,
  codes: string[],
): URLSearchParams {
  const next = withoutParams(params, [axis]);
  codes.forEach((code) => next.append(axis, code));
  return next;
}

function withSelection(
  params: URLSearchParams,
  selection: GroupSelection,
): URLSearchParams {
  const next = withCodes(params, "group", selection.groups);
  return withCodes(next, "situation", selection.situations);
}

function withToggledDomain(
  params: URLSearchParams,
  code: string,
): URLSearchParams {
  return withCodes(
    params,
    "domain",
    toggled(readCodes(params, "domain"), code),
  );
}

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
