interface OffsetPage {
  offset: number;
  limit: number;
  total: number;
}

/** Number of pages in the complete result; zero for an empty or unsized one. */
export function pageCount(total: number, limit: number): number {
  if (total <= 0 || limit <= 0) return 0;
  return Math.ceil(total / limit);
}

/** One-based page that contains `offset`. */
export function currentPage(offset: number, limit: number): number {
  return Math.floor(offset / limit) + 1;
}

/** Offset of the first row of a one-based page. */
export function offsetForPage(page: number, limit: number): number {
  return (page - 1) * limit;
}

/** One-based, inclusive row range of the page, clamped to the total. */
export function rangeOf({ offset, limit, total }: OffsetPage) {
  return { from: offset + 1, to: Math.min(offset + limit, total) };
}

/** True when the offset lies inside the result, so page numbers mean something. */
export function isOffsetInResult({ offset, total }: OffsetPage): boolean {
  return Number.isInteger(offset) && offset >= 0 && offset < total;
}

/** True when `page` is a whole number between one and the last page. */
export function isNavigablePage(state: OffsetPage, page: number): boolean {
  const last = pageCount(state.total, state.limit);
  return Number.isInteger(page) && page >= 1 && page <= last;
}
