import { formatNumber } from "../../../utils/format/formatNumber";

const UNITS = ["B", "KB", "MB", "GB", "TB"];
const STEP = 1024;

function unitIndex(bytes: number): number {
  if (bytes < STEP) return 0;
  return Math.min(
    Math.floor(Math.log(bytes) / Math.log(STEP)),
    UNITS.length - 1,
  );
}

/** Binary size with one decimal at most ("1.5 KB"); negative and non-finite input counts as zero. */
export function formatBytes(bytes: number, locale: string): string {
  const size = Number.isFinite(bytes) ? Math.max(bytes, 0) : 0;
  const index = unitIndex(size);
  return `${formatNumber(size / STEP ** index, locale)} ${UNITS[index]}`;
}
