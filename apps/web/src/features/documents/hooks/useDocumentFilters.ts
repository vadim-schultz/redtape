import { useSearchParams } from "react-router-dom";

export type FilterAxis = "domain" | "situation";

export interface DocumentFilters {
  domains: string[];
  situations: string[];
  toggleDomain: (code: string) => void;
  toggleSituation: (code: string) => void;
  clear: () => void;
}

function readCodes(params: URLSearchParams, axis: FilterAxis): string[] {
  return [...new Set(params.getAll(axis).filter(Boolean))];
}

function toggled(codes: string[], code: string): string[] {
  return codes.includes(code)
    ? codes.filter((c) => c !== code)
    : [...codes, code];
}

/** URL search params are the single source of truth for list filters. */
export function useDocumentFilters(): DocumentFilters {
  const [params, setParams] = useSearchParams();

  const toggle = (axis: FilterAxis, code: string) =>
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete(axis);
      toggled(readCodes(prev, axis), code).forEach((c) => next.append(axis, c));
      return next;
    });

  return {
    domains: readCodes(params, "domain"),
    situations: readCodes(params, "situation"),
    toggleDomain: (code) => toggle("domain", code),
    toggleSituation: (code) => toggle("situation", code),
    clear: () => setParams(new URLSearchParams()),
  };
}
