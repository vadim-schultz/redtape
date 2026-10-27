/** Share of the cap, as a fraction, from which stored bytes count as nearly full. */
const WARNING_NUMERATOR = 4;
const WARNING_DENOMINATOR = 5;

/** True once ``bytes`` reach 80 percent of ``cap``; a zero cap never warns. Integer math keeps the edge exact. */
export function nearsStorageCap(bytes: number, cap: number): boolean {
  if (cap <= 0) return false;
  return bytes * WARNING_DENOMINATOR >= cap * WARNING_NUMERATOR;
}
