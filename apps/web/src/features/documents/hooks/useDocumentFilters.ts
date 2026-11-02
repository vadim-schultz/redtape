import { useSearchParams } from "react-router-dom";

export type FilterAxis = "domain" | "situation";

export interface DocumentFilters {
  domains: string[];
  situations: string[];
  toggleDomain: (code: string) => void;
  toggleSituation: (code: string) => void;
  /** Drops the chips and returns to the first page; search and sort stay. */
  clear: () => void;
  /** Drops the chips and the search term and returns to the first page; sort stays. */
  clearAll: () => void;
}

const FILTER_PARAMS = ["domain", "situation"];

function readCodes(params: URLSearchParams, axis: FilterAxis): string[] {
  return [...new Set(params.getAll(axis).filter(Boolean))];
}

function toggled(codes: string[], code: string): string[] {
  return codes.includes(code)
    ? codes.filter((c) => c !== code)
    : [...codes, code];
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

/** URL search params are the single source of truth for list filters. */
export function useDocumentFilters(): DocumentFilters {
  const [params, setParams] = useSearchParams();

  const toggle = (axis: FilterAxis, code: string) =>
    setParams((prev) => {
      const next = withoutParams(prev, [axis]);
      toggled(readCodes(prev, axis), code).forEach((c) => next.append(axis, c));
      return next;
    });

  return {
    domains: readCodes(params, "domain"),
    situations: readCodes(params, "situation"),
    toggleDomain: (code) => toggle("domain", code),
    toggleSituation: (code) => toggle("situation", code),
    clear: () => setParams((prev) => withoutParams(prev, FILTER_PARAMS)),
    clearAll: () =>
      setParams((prev) => withoutParams(prev, [...FILTER_PARAMS, "q"])),
  };
}
