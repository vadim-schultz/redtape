const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["day", 86_400],
  ["hour", 3_600],
  ["minute", 60],
];

/** Coarsest whole unit that fits the elapsed seconds, falling back to "just now". */
function pickUnit(
  elapsedSeconds: number,
): [Intl.RelativeTimeFormatUnit, number] | null {
  for (const [unit, secondsPerUnit] of UNITS) {
    const value = Math.floor(elapsedSeconds / secondsPerUnit);
    if (value >= 1) return [unit, value];
  }
  return null;
}

export function formatRelativeTime(
  isoDate: string,
  locale: string,
  now: Date = new Date(),
): string {
  const elapsedSeconds = Math.max(
    0,
    (now.getTime() - new Date(isoDate).getTime()) / 1000,
  );
  const picked = pickUnit(elapsedSeconds);
  const formatter = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  if (!picked) return formatter.format(0, "second");

  const [unit, value] = picked;
  return formatter.format(-value, unit);
}
