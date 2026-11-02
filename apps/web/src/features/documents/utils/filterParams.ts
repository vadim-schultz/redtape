import { toggled, type GroupSelection } from "./groupSelection";

/** The URL params the chips are stored in. */
export const FILTER_PARAMS = ["domain", "group", "situation"] as const;

/** One chip axis of the documents list URL. */
export type FilterAxis = (typeof FILTER_PARAMS)[number];

/** The distinct, non-empty codes of `axis` in URL order. */
export function readCodes(params: URLSearchParams, axis: FilterAxis): string[] {
  return [...new Set(params.getAll(axis).filter(Boolean))];
}

/** The group and situation chips in effect. */
export function readSelection(params: URLSearchParams): GroupSelection {
  return {
    groups: readCodes(params, "group"),
    situations: readCodes(params, "situation"),
  };
}

/** A copy of `params` without `names`; any change of the filters also leaves the current page. */
export function withoutParams(
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

/** `params` with the group and situation chips replaced by `selection`. */
export function withSelection(
  params: URLSearchParams,
  selection: GroupSelection,
): URLSearchParams {
  const next = withCodes(params, "group", selection.groups);
  return withCodes(next, "situation", selection.situations);
}

/** `params` with the domain `code` switched on or off. */
export function withToggledDomain(
  params: URLSearchParams,
  code: string,
): URLSearchParams {
  return withCodes(
    params,
    "domain",
    toggled(readCodes(params, "domain"), code),
  );
}
